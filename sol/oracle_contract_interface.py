import os
import json
from app_logger.logger import Logger
from .contract_interface_base import ContractInterfaceBase


class OracleContractInterface(ContractInterfaceBase):
    def __init__(self, address: str, provider, protocol_name: str):
        cur_dir = os.path.dirname(__file__)
        abi_file_path = os.path.join(cur_dir, f'contracts/abi/{protocol_name}_ORACLE.json')
        with open(abi_file_path) as abi_json:
            abi = json.load(abi_json)

        self.logger = Logger(section_name=__name__)

        super().__init__(address, abi, provider)

    def get_asset_price(self, asset_address: str):
        contract_function_handle = self.contract_handle.functions.getAssetPrice(asset_address)
        self.logger.info(f"Calling contract function: {contract_function_handle}")

        asset_price = contract_function_handle.call()
        self.logger.info(f"Asset {asset_address} price: {asset_price} GWEI")
        return asset_price

    def get_asset_price_usd(self, asset_address: str):
        contract_function_handle = self.contract_handle.functions.getAssetPriceUsd(asset_address)

        self.logger.info(f"Calling contract function: {contract_function_handle}")

        asset_price = contract_function_handle.call()
        asset_price_usd = asset_price / 10 ** 8
        self.logger.info(f"Asset {asset_address} price: ${asset_price_usd}")

        return asset_price_usd
