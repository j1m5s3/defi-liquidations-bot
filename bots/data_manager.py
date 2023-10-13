from db.mongo_db_interface import MongoInterface


class DataManager(MongoInterface):
    def __init__(self, db_name: str, connection_url: str):
        super().__init__(db_name, connection_url)