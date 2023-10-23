import pandas as pd

from app_logger.logger import Logger
from enums.enums import QueueType
from db.mongo_db_interface import MongoInterface
from db.redis_interface import RedisInterface


class DataManager:
    """
    This class is responsible for managing the data that is stored in the database.

    :param db_interface: The database interface that is used to interact with the database.
    :param data_manager_queue: The queue that is used to communicate with the data manager.
    """
    def __init__(self, db_interface: MongoInterface, redis_interface: RedisInterface):
        self.db_interface: MongoInterface = db_interface
        self.redis_interface: RedisInterface = redis_interface

        logger_section_name = f"{__class__}"
        self.logger = Logger(section_name=logger_section_name)

    def insert_or_update_account_record(self, account_records: pd.DataFrame):
        """
        Insert or update account records in the database. Will search the DB for existing record, and update if found.
        Otherwise, will insert a new record.

        :param account_records: The account records to insert or update.
        """
        self.logger.info("Inserting or updating account records")

        for account_record in account_records.to_dict('records'):
            result = self.db_interface.update(
                collection='user_account_positions',
                query={
                    'protocol_name': account_record['protocol_name'],
                    'account_address': account_record['account_address'],
                },
                document={"$set": account_record},
                upsert=True
            )

            if result.matched_count == 0:
                self.logger.info(f"Inserted new account record: {account_record}")
            elif result.modified_count == 1:
                self.logger.info(f"Updated account record: {account_record}")

        return

    def monitor_queue(self, run_indefinitely: bool = True):
        """
        Monitor the data manager queue for new data to process.

        :param run_indefinitely: Whether to run the queue monitor indefinitely.
        """
        run = True
        while run:
            account_records = None
            
            if not run_indefinitely:
                run = False

            # Block until data is received
            self.logger.info("Waiting for data..")
            try:
                account_records: pd.DataFrame = self.redis_interface.pop_item(queue_type=QueueType.DATA_MANAGER_QUEUE)
            except Exception as e:
                self.logger.error(f"Error getting data from queue: {e}")

            if account_records is not None and not account_records.empty:
                self.logger.info("Received data..")
                self.insert_or_update_account_record(account_records=account_records)
            else:
                self.logger.info("No data received..")

            #self.data_manager_queue.task_done()

