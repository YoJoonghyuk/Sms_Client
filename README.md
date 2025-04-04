# Sms_Client
Этот клиент предназначен для отправки SMS-сообщений через HTTP API. Он принимает параметры из командной строки и файла конфигурации, формирует HTTP-запрос и отправляет его на указанный сервис. Полученный ответ выводится в консоль.

## Установка
1.  Клонируйте репозиторий: `git clone <ваш_репозиторий>`
2.  Перейдите в директорию проекта: `cd <директория_проекта>`
3.  Установите необходимые библиотеки: `pip install toml`

## Настройка
Создайте файл `config.toml` в корневой директории проекта. Пример в файле `config.toml`

## Запуск
Запустите скрипт client.py с необходимыми аргументами: python sms_client.py --config config.toml --sender 1234567890 --recipient 0987654321 --message "Тестовое сообщение"

Аргументы командной строки:
1. --config: Путь к файлу конфигурации TOML.
2. --sender: Номер телефона отправителя.
3. --recipient: Номер телефона получателя.
4. --message: Текст SMS-сообщения.

Логи записываются в файл sms_client.log.

## Структура проекта
sms_client.py: Основной файл скрипта.
config.toml: Пример файла конфигурации.
sms_client.log: Файл логов.
README.md: Этот файл.
