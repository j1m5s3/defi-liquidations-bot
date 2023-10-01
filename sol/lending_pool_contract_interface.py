import os
import json
from typing import Dict, Optional
from web3 import Web3
from web3.logs import DISCARD

from enums.enums import LendingProtocol

from app_logger.logger import Logger
from .contract_interface_base import ContractInterfaceBase


class LendingPoolContractInterface(ContractInterfaceBase):
    def __init__(self, address: str, provider, protocol_name: str):
        cur_dir = os.path.dirname(__file__)
        abi_file_path = os.path.join(cur_dir, f'contracts/abi/lending_protocols/{protocol_name}.json')
        with open(abi_file_path) as abi_json:
            abi = json.load(abi_json)

        self.protocol_name = protocol_name

        logger_section_name = f"{__name__}.{protocol_name}"
        self.logger = Logger(section_name=logger_section_name)

        super().__init__(address, abi, provider)

        if protocol_name == LendingProtocol.AAVE_ARBITRUM.name or LendingProtocol.RADIANT_ARBITRUM.name:
            self.events = self.get_event_logs("Borrow", blocks_back=100000)
