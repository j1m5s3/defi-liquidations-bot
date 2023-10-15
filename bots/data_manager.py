import pandas as pd
from queue import Queue

from app_logger.logger import Logger

from db.mongo_db_interface import MongoInterface


class DataManager:
    """
    This class is responsible for managing the data that is stored in the database.

    :param db_interface: The database interface that is used to interact with the database.
    :param data_manager_queue: The queue that is used to communicate with the data manager.
    """
    def __init__(self, db_interface: MongoInterface, data_manager_queue):
        self.db_interface: MongoInterface = db_interface
        self.data_manager_queue: Queue = data_manager_queue

        logger_section_name = f"{__class__}"
        self.logger = Logger(section_name=logger_section_name)

    def insert_or_update_account_record(self, account_records: pd.DataFrame):
        """
        Insert or update account records in the database. Will search the DB for existing record, and update if found.
        Otherwise, will insert a new record.

        :param account_records: The account records to insert or update.
        """
        self.logger.info("Inserting or updating account records")

        for account_record in account_records.to_records():
            result = self.db_interface.update(
                collection='user_account_positions',
                query={
                    'protocol_name': account_record['protocol_name'],
                    'user_address': account_record['user_address'],
                },
                document=account_record

            )

            if result.matched_count == 0:
                self.logger.info(f"Inserting new account record: {account_record}")
            elif result.modified_count == 1:
                self.logger.info(f"Updating account record: {account_record}")

        return

    def monitor_queue(self):
        """
        Monitor the data manager queue for new data to process.
        """
        while True:
            # Block until data is received
            account_records: pd.DataFrame = self.data_manager_queue.get(block=True)
            self.logger.info("Received data..")

            if account_records:
                self.insert_or_update_account_record(account_records=account_records)

            self.data_manager_queue.task_done()

