import argparse
import socket
import ssl
import toml
import logging
import sys
import base64
import json
from typing import Dict

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
        self.status_code: int = status_code 
        self.body: str = body 

    @classmethod
    def from_bytes(cls, binary_data: bytes) -> "HTTPResponse":
        try:
            response_str: str = binary_data.decode('utf-8') 
            header_body_split: list[str] = response_str.split('\r\n\r\n', 1)
            
            if len(header_body_split) != 2: 
                logging.error(f"Не удалось разделить заголовки и тело ответа. Ответ: {response_str}")  
                return cls(500, '{"error": "Internal Server Error: Не удалось распарсить ответ"}') 

            headers_str: str = header_body_split[0] 
            body: str = header_body_split[1] 

            first_line: str = headers_str.split('\r\n')[0]  
            status_code: int = int(first_line.split(' ')[1])  
            
            return cls(status_code, body)  
        except Exception as e:
            logging.error(f"Ошибка при парсинге ответа: {e}")  
            return cls(500, f'{{"error": "Internal Server Error: Ошибка парсинга: {e}"}}') 

def send_sms(config: Dict[str, str], sender: str, recipient: str, message: str) -> HTTPResponse:
    host: str = config['address']  
    username: str = config['username']  
    password: str = config['password']  
    use_ssl: bool = config.get('use_ssl', False)  

    path: str = "/send_sms"  

    body_dict: Dict[str, str] = {"sender": sender, "recipient": recipient, "message": message} 
    body: bytes = json.dumps(body_dict).encode('utf-8') 

    auth_string: str = f"{username}:{password}" 
    auth_bytes: bytes = auth_string.encode('utf-8')  
    auth_base64: str = base64.b64encode(auth_bytes).decode('utf-8')  

    headers: Dict[str, str] = {
        "Authorization": f"Basic {auth_base64}",  
        "Content-Type": "application/json",  
        "Content-Length": str(len(body))  
    }

    request: str = f"POST {path} HTTP/1.1\r\n"  
    request += f"Host: {host}\r\n" 
    for key, value in headers.items(): 
        request += f"{key}: {value}\r\n"
    request += "\r\n"  
    request += body.decode('utf-8') 

    logging.debug(f"Отправляем запрос: {request}")  

    try:
        host_parts: list[str] = host.split(":") 
        hostname: str = host_parts[0]  
        port: int = int(host_parts[1]) if len(host_parts) > 1 else 80 

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:  
            sock.connect((hostname, port))  

            if use_ssl: 
                context: ssl.SSLContext = ssl.create_default_context()
                sock: socket.socket = context.wrap_socket(sock, server_hostname=hostname)

            sock.sendall(request.encode('utf-8')) 

            response_bytes: bytes = b""  
            while True:  
                chunk: bytes = sock.recv(4096)  
                if not chunk:  
                    break
                response_bytes += chunk  

            response: str = response_bytes.decode('utf-8')  
            logging.debug(f"Получен ответ: {response}")  

            try:
                status_line: str = response.split('\r\n')[0]  
                status_code: int = int(status_line.split(' ')[1]) 
                body_start: int = response.find('\r\n\r\n') + 4  
                response_body: str = response[body_start:]  
                return HTTPResponse(status_code, response_body)  
            except Exception as e:  
                logging.error(f"Ошибка при парсинге ответа: {e}")  
                return HTTPResponse(500, f'{{"error": "Internal Server Error: Ошибка парсинга ответа: {e}"}}')  

    except Exception as e: 
        logging.error(f"Ошибка при отправке запроса: {e}")  
        return HTTPResponse(500, f'{{"error": "Internal Server Error: {e}"}}') 
    
def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="CLI клиент для отправки SMS.")
    parser.add_argument("--config", required=True, help="Путь к файлу конфигурации TOML.")
    parser.add_argument("--sender", required=True, help="Номер отправителя SMS.")
    parser.add_argument("--recipient", required=True, help="Номер получателя SMS.")
    parser.add_argument("--message", required=True, help="Текст SMS сообщения.")

    args: argparse.Namespace = parser.parse_args()

    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config: Dict[str, str] = toml.load(f)
    except FileNotFoundError:
        logging.error(f"Файл конфигурации не найден: {args.config}")
        print(f"Ошибка: Файл конфигурации не найден: {args.config}")
        sys.exit(1)
    except toml.TomlDecodeError as e:
        logging.error(f"Ошибка при чтении файла конфигурации: {args.config}")
        print(f"Ошибка: Ошибка при чтении файла конфигурации: {e}")
        sys.exit(1)

    response: HTTPResponse = send_sms(config, args.sender, args.recipient, args.message)

    print(f"Код ответа: {response.status_code}")
    if response.body:
        print(f"Тело ответа: {response.body}")
    else:
        print("Тело ответа: (пусто)")

if __name__ == "__main__":
    main()
