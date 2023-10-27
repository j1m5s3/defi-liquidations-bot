import os
import json
from typing import Dict, Optional, List
from retrying import retry
from web3 import Web3
from web3.logs import DISCARD

from enums.enums import LendingProtocol
from db.schemas.position_schema import BorrowEvent

from app_logger.logger import Logger
from .contract_interface_base import ContractInterfaceBase
from .provider.provider import Provider


class LendingPoolContractInterface(ContractInterfaceBase):
    def __init__(self, address: str, provider: Provider, protocol_name: str):
        cur_dir = os.path.dirname(__file__)
        abi_file_path = os.path.join(cur_dir, f'contracts/abi/lending_protocols/{protocol_name}_LENDING_POOL.json')
        with open(abi_file_path) as abi_json:
            abi = json.load(abi_json)

        self.protocol_name = protocol_name

        logger_section_name = f"{__name__}.{protocol_name}"
        self.logger = Logger(section_name=logger_section_name)

        super().__init__(address, abi, provider)

        if protocol_name == LendingProtocol.AAVE_ARBITRUM.name or LendingProtocol.RADIANT_ARBITRUM.name:
            self.events = self.get_event_logs("Borrow", blocks_back=100000)
            self.recent_borrowers = self.__extract_account_addresses(self.events, "Borrow")

    def __extract_account_addresses(self, event_logs: List[Dict], event_name: str):
        account_addresses = []
        if event_name == "Borrow":
            self.logger.info(f"Found {len(event_logs)} {event_name} event logs")
            self.logger.info(f"Extracting account addresses from {event_name} event logs")
            for event_log in event_logs:
                account_addresses.append(BorrowEvent().load(dict(event_log[event_name])))
        return account_addresses

    @retry(stop_max_attempt_number=3, wait_fixed=2000, retry_on_exception=lambda e: isinstance(e, Exception))
    def get_user_account_data(self, user_address: str):
        self.logger.info(f"Getting user account data for {user_address} from {self.protocol_name} contract")

        contract_function_handle = self.contract_handle.functions.getUserAccountData(user_address)
        try:
            account_data = contract_function_handle.call()
            self.logger.info(f"User account data for {user_address}: {account_data}")
        except Exception as e:
            self.logger.error(f"Failed to get user account data for {user_address}: {e}")
            account_data = None

        return account_data

    def refresh_contract_data(self):
        self.logger.info("Refreshing contract data")

        self.events = self.get_event_logs("Borrow", blocks_back=100000)
        self.recent_borrowers = self.__extract_account_addresses(self.events, "Borrow")

