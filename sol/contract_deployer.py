from typing import Optional, Dict, Any
import os
from web3 import Web3
from retrying import retry
from solcx import compile_files, install_solc, set_solc_version_pragma, install_solc_pragma

from .provider.provider import Provider

pragma = '0.8.10'
#pragma = '0.7.6'

install_solc_pragma(pragma_string=pragma, show_progress=True)
set_solc_version_pragma(pragma)


# install_solc(version='latest', show_progress=True)


# Compile and deploy the contract
class ContractDeployer:
    def __init__(
            self,
            provider: Provider,
            contract_source_path: str,
            contract_name: str,
            constructor_args: Dict = None
    ):
        """
        :param provider: type: Provider - Provider object
        :param contract_source_path: type: str - Path to the contract source file
        :param contract_name: type: str - Name of the contract
        :param constructor_args: type: Dict - Arguments for the contract constructor

        Description:
            Class for deploying smart contracts
        """
        self.provider = provider
        self.deploy_status = False
        self.contract_source_path = contract_source_path
        self.contract_name = contract_name
        self.constructor_args = constructor_args

    def __compile_contract(self) -> Optional[Dict]:
        contract_id = None
        compiled_sol = compile_files(source_files=self.contract_source_path, output_values=['abi', 'bin'])

        for key in compiled_sol.keys():
            if self.contract_name in key:
                contract_id = key

        if contract_id is None:
            raise Exception("Contract ID not found")

        contract_interface = compiled_sol[contract_id]
        compiled_bytecode = contract_interface['bin']
        compiled_abi = contract_interface['abi']

        return {"compiled_bytecode": compiled_bytecode, "compiled_abi": compiled_abi}

    @retry(stop_max_attempt_number=5, wait_fixed=1000)
    def __create_signed_txn(self, compiled_abi, compiled_bytecode) -> Any:
        """
        Create and send txn to deploy contract to ETHEREUM network
        :param compiled_abi: compliled json interface for contract
        :param compiled_bytecode: compiled bytecode for contract
        :param constructor_args: arguments for contract constructor
        :return:
        """
        contract = self.provider.w3.eth.contract(abi=compiled_abi, bytecode=compiled_bytecode)

        txn = {
            "from": self.provider.get_wallet_address(),
            "nonce": self.provider.get_nonce()
        }

        if self.constructor_args is None:
            constructor = contract.constructor().build_transaction(txn)
        else:
            constructor = contract.constructor(**self.constructor_args).build_transaction(txn)

        signed_txn = self.provider.w3.eth.account.sign_transaction(constructor,
                                                                   private_key=self.provider.get_wallet_private_key())

        return signed_txn

    def __send_signed_txn(self, signed_txn):
        send_txn = self.provider.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_receipt = self.provider.w3.eth.wait_for_transaction_receipt(send_txn)

        return txn_receipt

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def deploy(self):
        compiled_contract = self.__compile_contract()

        byte_code = compiled_contract["compiled_bytecode"]
        abi = compiled_contract["compiled_abi"]

        signed_txn = self.__create_signed_txn(compiled_abi=abi,
                                              compiled_bytecode=byte_code)

        txn_receipt = self.__send_signed_txn(signed_txn=signed_txn)
        if txn_receipt['status'] == 1:
            self.deploy_status = True
            return {
                "txn_receipt": txn_receipt,
                "contract_address": txn_receipt['contractAddress'],
                "abi": abi
            }
        elif txn_receipt['status'] == 0:
            raise Exception("Contract deployment failed {}".format(txn_receipt))
