import argparse
import socket
import ssl
import toml
import logging
import sys
import base64
from typing import Dict
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("sms_client.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class HTTPResponse:
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body

    @classmethod
    def from_bytes(cls, binary_data: bytes) -> "HTTPResponse":
        try:
            response_str = binary_data.decode('utf-8')
            header_body_split = response_str.split('\r\n\r\n', 1)
            
            if len(header_body_split) != 2:
                logging.error(f"Не удалось разделить заголовки и тело ответа. Ответ: {response_str}")
                return cls(500, '{"error": "Не удалось распарсить ответ"}')

            headers_str, body = header_body_split
            
            first_line = headers_str.split('\r\n')[0]
            status_code = int(first_line.split(' ')[1])
            
            return cls(status_code, body)
        except Exception as e:
            logging.error(f"Ошибка при парсинге ответа: {e}")
            return cls(500, f'{{"error": "Ошибка парсинга: {e}"}}')

def send_sms(config: Dict[str, str], sender: str, recipient: str, message: str) -> HTTPResponse:
    host = config['address']
    username = config['username']
    password = config['password']
    use_ssl = config.get('use_ssl', False) 

    path = "/send_sms" 
    body_dict = {"sender": sender, "recipient": recipient, "message": message}
    body = json.dumps(body_dict).encode('utf-8') 

    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body))  
    }

    request = f"POST {path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    for key, value in headers.items():
        request += f"{key}: {value}\r\n"
    request += "\r\n"
    request += body.decode('utf-8')

    logging.debug(f"Отправляем запрос: {request}")

    try:
        host_parts = host.split(":")
        hostname = host_parts[0]
        port = int(host_parts[1]) if len(host_parts) > 1 else 80 

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((hostname, port))

            if use_ssl:  
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=hostname)

            sock.sendall(request.encode('utf-8')) 

            response_bytes = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_bytes += chunk

            response = response_bytes.decode('utf-8')
            logging.debug(f"Получен ответ: {response}")

            try:
                status_line = response.split('\r\n')[0]
                status_code = int(status_line.split(' ')[1])
                body_start = response.find('\r\n\r\n') + 4
                response_body = response[body_start:]
                return HTTPResponse(status_code, response_body)
            except Exception as e:
                logging.error(f"Ошибка при парсинге ответа: {e}")
                return HTTPResponse(500, f'{{"error": "Ошибка парсинга ответа: {e}"}}')


    except Exception as e:
        logging.error(f"Ошибка при отправке запроса: {e}")
        return HTTPResponse(500, f'{{"error": "{e}"}}')

def main():
    parser = argparse.ArgumentParser(description="CLI клиент для отправки SMS.")
    parser.add_argument("--config", required=True, help="Путь к файлу конфигурации TOML.")
    parser.add_argument("--sender", required=True, help="Номер отправителя SMS.")
    parser.add_argument("--recipient", required=True, help="Номер получателя SMS.")
    parser.add_argument("--message", required=True, help="Текст SMS сообщения.")

    args = parser.parse_args()

    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = toml.load(f)
    except FileNotFoundError:
        logging.error(f"Файл конфигурации не найден: {args.config}")
        print(f"Ошибка: Файл конфигурации не найден: {args.config}")
        sys.exit(1)
    except toml.TomlDecodeError as e:
        logging.error(f"Ошибка при чтении файла конфигурации: {args.config}")
        print(f"Ошибка: Ошибка при чтении файла конфигурации: {e}")
        sys.exit(1)

    response = send_sms(config, args.sender, args.recipient, args.message)

    print(f"Код ответа: {response.status_code}")
    if response.body:
        print(f"Тело ответа: {response.body}")
    else:
        print("Тело ответа: (пусто)")

if __name__ == "__main__":
    main()