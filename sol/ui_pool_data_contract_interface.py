import os
import json
from typing import Dict, Optional, List
from web3 import Web3
from web3.logs import DISCARD
from dotenv import dotenv_values, find_dotenv

from enums.enums import LendingProtocol
from db.schemas.position_schema import BorrowEvent

from app_logger.logger import Logger
from .contract_interface_base import ContractInterfaceBase

config = dotenv_values(dotenv_path=find_dotenv())


class UIPoolDataContractInterface(ContractInterfaceBase):
    def __init__(self, address: str, provider, protocol_name: str):
        cur_dir = os.path.dirname(__file__)
        abi_file_path = os.path.join(
            cur_dir, f'contracts/abi/lending_protocols/{protocol_name}_UI_POOL_DATA_PROVIDER.json'
        )
        with open(abi_file_path) as abi_json:
            abi = json.load(abi_json)

        self.protocol_name = protocol_name

        logger_section_name = f"{__name__}.{protocol_name}"
        self.logger = Logger(section_name=logger_section_name)

        if protocol_name == LendingProtocol.AAVE_ARBITRUM.name:
            self.address_provider_address = config["AAVE_ARBITRUM_POOL_CONTRACT_ADDRESS_PROVIDER"]
        elif protocol_name == LendingProtocol.RADIANT_ARBITRUM.name:
            self.address_provider_address = config["RADIANT_ARBITRUM_POOL_CONTRACT_ADDRESS_PROVIDER"]
        elif protocol_name == LendingProtocol.SILO_ARBITRUM.name:
            self.address_provider_address = config["SILO_ARBITRUM_POOL_CONTRACT_ADDRESS_PROVIDER"]
        else:
            raise Exception("Unknown protocol name")

        super().__init__(address, abi, provider)

    def get_user_reserves_data(self, user_address: str):
        contract_function_handle = self.contract_handle.functions.getUserReservesData(
            self.address_provider_address,
            user_address
        )

        self.logger.info(f"Calling contract function: {contract_function_handle}")
        return contract_function_handle.call()

