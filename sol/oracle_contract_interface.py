import os
import json
from app_logger.logger import Logger
from .contract_interface_base import ContractInterfaceBase
from .provider.provider import Provider


class OracleContractInterface(ContractInterfaceBase):
    """
    Oracle contract interface
    """
    def __init__(self, address: str, provider: Provider, protocol_name: str):
        """
        Inintialize oracle contract interface
        :param address:
        :param provider:
        :param protocol_name:
        """
        cur_dir = os.path.dirname(__file__)
        abi_file_path = os.path.join(
            cur_dir, f'contracts/abi/lending_protocols/{protocol_name}_ORACLE.json'
        )
        with open(abi_file_path) as abi_json:
            abi = json.load(abi_json)

        self.logger = Logger(section_name=__name__)

        super().__init__(address, abi, provider)

    def get_asset_price(self, asset_address: str):
        """
        Get asset price in GWEI given asset address
        :param asset_address:
        :return: Asset price in GWEI
        """
        contract_function_handle = self.contract_handle.functions.getAssetPrice(asset_address)
        self.logger.info(f"Calling contract function: {contract_function_handle}")

        try:
            asset_price = contract_function_handle.call()
            self.logger.info(f"Asset {asset_address} price: {asset_price} GWEI")
        except Exception as e:
            self.logger.error(f"Failed to get asset price for {asset_address}: {e}")
            asset_price = 0

        return asset_price

    def get_asset_price_usd(self, asset_address: str):
        """
        Get asset price in USD given asset address
        :param asset_address:
        :return: Asset price in USD
        """
        contract_function_handle = self.contract_handle.functions.getAssetPrice(asset_address)

        self.logger.info(f"Calling contract function: {contract_function_handle}")
        try:
            asset_price = contract_function_handle.call()
            asset_price_usd = asset_price / 10 ** 8
            self.logger.info(f"Asset {asset_address} price: ${asset_price_usd}")
        except Exception as e:
            self.logger.error(f"Failed to get asset price for {asset_address}: {e}")
            asset_price_usd = 0

        return asset_price_usd
