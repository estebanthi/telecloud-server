from telethon import TelegramClient
from yaml import safe_load


class Telegram:
    def __init__(self):
        with open("config.yaml", "r") as config_file:
            config = safe_load(config_file)

        telegram_api_id = config["telegram_api_id"]
        telegram_api_hash = config["telegram_api_hash"]

        self.telegram_client = TelegramClient("session", telegram_api_id, telegram_api_hash)
        self.telegram_client.start()

        self.telegram_max_file_size = int(1024 * 1024 * 1024 * 2) # 2 GB
        self.chanel_name = config["telegram_chanel"]
