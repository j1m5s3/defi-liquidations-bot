import os
from typing import Dict, Optional
from web3 import Web3
from web3.logs import DISCARD

from app_logger.logger import Logger
from .contract_interface_base import ContractInterfaceBase


class FlashLiquidateContractInterface(ContractInterfaceBase):
    def __init__(self, address: str, abi: list, provider):
        super().__init__(address, abi, provider)

        self.logger = Logger(section_name=__name__)

    def flash_loan_liquidate(
            self,
            token0,
            loan_amount,
            liquidate_params
    ):
        """
        Description:
            This function is used to liquidate a position using flash loans.

        :param token0: Address of token0
        :param loan_amount: Amount of token0 to borrow
        :param liquidate_params: List of params for liquidate
        :return: Receipt of transaction
        """

        token0 = Web3.to_checksum_address(token0)

        if not isinstance(loan_amount, int):
            loan_amount = Web3.to_wei(loan_amount, "ether")

        contract_function_handle = self.contract_functions().flashLoanLiquidate(
            token0,
            loan_amount,
            liquidate_params,
        )
        try:
            txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
            if txn_receipt["status"] == 0:
                raise Exception("Transaction failed")
            elif txn_receipt["status"] == 1:
                print("Transaction succeeded", flush=True)

            event_logs = self.__get_event_logs(txn_receipt, event_name="FlashLoanResult")
        except Exception as e:
            self.logger.error(f"Error in flash_loan_liquidate: {e}")
            return

        return txn_receipt
