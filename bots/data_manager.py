import pandas as pd

from db.mongo_db_interface import MongoInterface


class DataManager:
    """
    This class is responsible for managing the data that is stored in the database.

    :param db_interface: The database interface that is used to interact with the database.
    :param data_manager_queue: The queue that is used to communicate with the data manager.
    """
    def __init__(self, db_interface: MongoInterface, data_manager_queue):
        self.db_interface = db_interface
        self.data_manager_queue = data_manager_queue

    def insert_new_account_records(self, account_records: pd.DataFrame):
        """
        Inserts new account records into the database.

        :param account_records: The account records that are to be inserted into the database.
        """
        self.db_interface.insert_many("account_records", account_records)

    def update_existing_account_records(self, account_records: pd.DataFrame):
        """
        Updates existing account records in the database.

        :param account_records: The account records that are to be updated in the database.
        """
        for _, account_record in account_records.iterrows():
            self.db_interface.update(
                "user_account_positions",
                {"account_address": account_record["account_address"]},
                account_record
            )
