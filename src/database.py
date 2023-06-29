from motor.motor_asyncio import AsyncIOMotorClient
from yaml import safe_load


class Database:

    def __init__(self):
        with open("config.yaml", "r") as config_file:
            config = safe_load(config_file)

        mongo_uri = config["mongo_uri"]
        mongo_client = AsyncIOMotorClient(mongo_uri)

        db_name = config["db_name"]
        self.db = mongo_client[db_name]
