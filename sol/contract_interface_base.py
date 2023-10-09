import json
import os
from typing import List, Dict
from web3 import Web3
from web3.logs import DISCARD

from app_logger.logger import Logger
from .provider.provider import Provider


# Interface for the contract
class ContractInterfaceBase:
    def __init__(self, address: str, abi: List[Dict], provider: Provider):
        self.address = address
        self.abi = abi
        self.provider = provider
        self.contract_handle = self.__create_contract_handler()

        self.logger = Logger(section_name=__name__)

        cur_dir = os.path.dirname(__file__)
        abi_file_path = os.path.join(cur_dir, 'contracts/abi/erc20_abi.json')
        with open(abi_file_path, "r") as f:
            self.erc_20_abi = json.load(f)

        self.erc20_max_approved = []

    def __create_contract_handler(self, is_erc20=False, contract_address=None):
        if is_erc20:
            return self.provider.w3.eth.contract(address=contract_address, abi=self.erc_20_abi)
        return self.provider.w3.eth.contract(address=self.address, abi=self.abi)

    def token_approve(self, token_address, amount=None):
        if amount is None:
            max_amount = 2 ** 64 - 1
            amount = Web3.to_wei(max_amount, "ether")

            if self.erc20_is_max_approved(token_address):
                return True
            else:
                self.erc20_max_approved.append(token_address)

        contract_handle = self.__create_contract_handler(is_erc20=True, contract_address=token_address)
        contract_function_handle = contract_handle.functions.approve(self.address, amount)
        txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
        if txn_receipt["status"] == 0:
            self.erc20_max_approved.remove(token_address)
            raise Exception("Transaction failed")

        return True

    def erc20_is_max_approved(self, token_address):
        if token_address not in self.erc20_max_approved:
            return False
        return True

    def token_transfer_from(self, token_address, amount):
        if token_address not in self.erc20_max_approved:
            return False

        contract_handle = self.__create_contract_handler(is_erc20=True, contract_address=token_address)
        contract_function_handle = contract_handle.functions.transferFrom(
            self.provider.get_wallet_address(),
            self.address,
            Web3.to_wei(amount, 'ether')
        )
        txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
        if txn_receipt["status"] == 0:
            raise Exception("Transaction failed")
        return True

    def get_token_balance(self, token_address, wallet=None, contract=None):
        contract_handle = self.__create_contract_handler(is_erc20=True, contract_address=token_address)
        if wallet:
            balance = contract_handle.functions.balanceOf(self.provider.get_wallet_address()).call()
            return Web3.from_wei(balance, "ether")
        elif contract:
            balance = contract_handle.functions.balanceOf(self.address).call()
            return Web3.from_wei(balance, "ether")

    def get_event_logs(self, event_name, from_block=None, to_block="latest", blocks_back=1000):
        events = []

        event_handle = getattr(self.event_handle(), event_name)()

        if from_block is None:
            from_block = self.provider.w3.eth.get_block_number() - blocks_back

        logs = event_handle.get_logs(fromBlock=from_block, toBlock=to_block)
        for log in logs:
            event_dict = {log.event: log.args}
            events.append(event_dict)
            self.logger.info(f"FOUND {event_name} --> {event_dict}")

        return events

    def contract_functions(self):
        return self.contract_handle.functions

    def send_txn(self, contract_function_handle, signing_needed=False):
        txn = {
            "from": self.provider.get_wallet_address(),
            "nonce": self.provider.get_nonce()
        }

        try:
            function_call = contract_function_handle.build_transaction(txn)
            if signing_needed:
                signed_txn = self.provider.w3.eth.account.sign_transaction(function_call,
                                                                           private_key=self.provider.get_wallet_private_key())
                send_txn = self.provider.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                txn_receipt = self.provider.w3.eth.wait_for_transaction_receipt(send_txn)
            else:
                txn_receipt = self.provider.w3.eth.send_transaction(function_call)
        except Exception as err:
            print(f"Error sending txn: {err}", flush=True)
            raise err

        return txn_receipt

    def get_address(self):
        return self.address

    def get_abi(self):
        return self.abi

    def event_handle(self):
        return self.contract_handle.events
