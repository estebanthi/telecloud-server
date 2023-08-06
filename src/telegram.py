from telethon import TelegramClient
from yaml import safe_load


class Telegram:
    def __init__(self):
        with open("config.yaml", "r") as config_file:
            config = safe_load(config_file)

        telegram_api_id = config["telegram_api_id"]
        telegram_api_hash = config["telegram_api_hash"]

        self.client = TelegramClient("session", telegram_api_id, telegram_api_hash)
        self.client.start()

        self.max_file_size = int(1024 * 1024 * 50)  # 50 MB
        self.chanel_name = config["telegram_chanel"]
