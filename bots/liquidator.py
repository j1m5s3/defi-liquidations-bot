import pandas
from typing import Dict
from dotenv import dotenv_values, find_dotenv
from queue import Queue

from app_logger.logger import Logger
from enums.enums import LendingProtocol
from bots.utils.utils import encode_path
from sol.flash_liquidate_contract_interface import FlashLiquidateContractInterface

config = dotenv_values(dotenv_path=find_dotenv())


class Liquidator:
    def __init__(
            self,
            flash_liquidate_contract_interface: FlashLiquidateContractInterface,
            liquidations_queue: Queue
    ):
        self.flash_liquidate_contract_interface = flash_liquidate_contract_interface
        self.liquidations_queue = liquidations_queue

        logger_section_name = f"{__class__}"
        self.logger = Logger(section_name=logger_section_name)

    def liquidate(self):
        while True:

            liquidation_data: Dict = self.liquidations_queue.get(block=True)
            self.logger.info("Received liquidation data..")

            collateral_asset = liquidation_data['collateral_asset']
            debt_asset = liquidation_data['debt_asset']
            user_address = liquidation_data['user_address']
            debt_to_cover = liquidation_data['debt_to_cover']
            receive_a_token = liquidation_data['receive_a_token']

            if liquidation_data['protocol_name'] == LendingProtocol.AAVE_ARBITRUM.name:
                protocol = LendingProtocol.AAVE_ARBITRUM.value
            elif liquidation_data['protocol_name'] == LendingProtocol.RADIANT_ARBITRUM.name:
                protocol = LendingProtocol.RADIANT_ARBITRUM.value
            else:
                self.logger.error("Unknown protocol name")
                raise Exception("Unknown protocol name")

            path = [collateral_asset, debt_asset, user_address, debt_to_cover, receive_a_token, protocol]
            path_types = ["address", "address", "address", "uint256", "bool", "uint8"]
            liquidation_encoded_params = encode_path(path=path, path_types=path_types)

            liquidation_result = self.flash_liquidate_contract_interface.flash_loan_liquidate(
                token0=debt_asset,
                loan_amount=debt_to_cover,
                liquidate_params=liquidation_encoded_params
            )

            self.logger.info(f"Liquidation result: {liquidation_result}")
