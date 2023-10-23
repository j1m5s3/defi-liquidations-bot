import json
import pandas as pd

from abc import ABC
from redis import Redis
from dotenv import dotenv_values, find_dotenv

from app_logger.logger import Logger
from enums.enums import QueueType

config = dotenv_values(dotenv_path=find_dotenv())


class RedisInterface(Redis, ABC):
    """
    Redis interface. Used to push and pop items from queue
    """
    def __init__(self, host, port):
        """
        Initialize RedisInterface class
        :param host:
        :param port:
        """
        super().__init__(host=host, port=port, decode_responses=True)

        logger_section_name = f"{__class__}"
        self.logger = Logger(section_name=logger_section_name)

    def push_item(self, queue_type: QueueType, value: dict | pd.DataFrame) -> bool:
        """
        Push item to queue
        :param value: Value to push to queue
        :param queue_type: Queue type
        :return: True or False
        """
        if isinstance(value, dict):
            value = json.dumps(value)
        elif isinstance(value, pd.DataFrame):
            value = value.to_json()
        else:
            raise Exception("Unknown type")

        result = self.rpush(queue_type.name, value)

        if result > 0:
            self.logger.info(f"Pushed item to queue: {queue_type.name}")
            return True

        self.logger.error(f"Failed to push item to queue: {queue_type.name}")
        return False

    def pop_item(self, queue_type: QueueType) -> dict | pd.DataFrame:
        """
        Pop item from queue

        :param queue_type: Queue type
        :return: Returns dict or pd.DataFrame depending on queue type
        """
        if queue_type == QueueType.LIQUIDATOR_QUEUE:
            data = self.lpop(queue_type.name)
            data = json.loads(data)
            self.logger.info(f"Received liquidation data from queue: {queue_type.name}")
        elif queue_type == QueueType.DATA_MANAGER_QUEUE:
            data = self.lpop(queue_type.name)
            data = pd.read_json(data)
            self.logger.info(f"Received data from queue: {queue_type.name}")
        else:
            raise Exception("Unknown queue type")

        return data
