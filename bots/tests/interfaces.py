import json

from dotenv import dotenv_values, find_dotenv

from app_logger.logger import Logger
from db.mongo_db_interface import MongoInterface

from enums.enums import (
    LendingProtocol,
    LendingPoolAddresses,
    LendingPoolUIDataContract,
    LendingPoolAddressesProvider
)

from sol.provider.provider import Provider
from sol.lending_pool_contract_interface import LendingPoolContractInterface
from sol.ui_pool_data_contract_interface import UIPoolDataContractInterface
from sol.oracle_contract_interface import OracleContractInterface
from sol.flash_liquidate_contract_interface import FlashLiquidateContractInterface

from bots.searcher import Searcher
from bots.data_manager import DataManager
from bots.liquidator import Liquidator

from bots.queues.queues import DATA_MANAGER_QUEUE, LIQUIDATIONS_QUEUE

config = dotenv_values(dotenv_path=find_dotenv())
logger = Logger(section_name=__file__)

flash_liquidate_contract_path = "../../sol/contracts/FlashLiquidate.json"
with open(flash_liquidate_contract_path, "r") as f:
    flash_liquidate_contract_json = json.load(f)

flash_liquidate_contract_address = flash_liquidate_contract_json['contract_address']
flash_liquidate_contract_abi = flash_liquidate_contract_json['abi']

try:
    provider = Provider(
        wallet_address=config["WALLET_ADDRESS"],
        wallet_private_key=config["WALLET_PRIVATE_KEY"],
        https_url=None,
        ws_url=config["ALCHEMY_WSS_RPC_URL_ARBITRUM"]
    )
    logger.info("Provider initialized")
except Exception as e:
    logger.error(f"Error: {e}")
    logger.critical("Failed to initialize provider")
    raise

db_interface = MongoInterface(
    db_name=config["MONGO_DB_NAME"],
    connection_url=config["MONGO_CONNECTION_URL"]
)

# Existing contract interfaces ################################################
lending_pool_interfaces = {
    LendingPoolAddresses.AAVE_ARBITRUM.name: LendingPoolContractInterface(
        address=LendingPoolAddresses.AAVE_ARBITRUM.value,
        provider=provider,
        protocol_name=LendingProtocol.AAVE_ARBITRUM.name
    ),
    LendingPoolAddresses.RADIANT_ARBITRUM.name: LendingPoolContractInterface(
        address=LendingPoolAddresses.RADIANT_ARBITRUM.value,
        provider=provider,
        protocol_name=LendingProtocol.RADIANT_ARBITRUM.name
    ),
    LendingPoolAddresses.SILO_ARBITRUM.name: LendingPoolContractInterface(
        address=LendingPoolAddresses.SILO_ARBITRUM.value,
        provider=provider,
        protocol_name=LendingProtocol.SILO_ARBITRUM.name
    )
}

ui_pool_data_interfaces = {
    LendingPoolUIDataContract.AAVE_ARBITRUM.name: UIPoolDataContractInterface(
        address=LendingPoolUIDataContract.AAVE_ARBITRUM.value,
        provider=provider,
        protocol_name=LendingPoolUIDataContract.AAVE_ARBITRUM.name
    ),
    LendingPoolUIDataContract.RADIANT_ARBITRUM.name: UIPoolDataContractInterface(
        address=LendingPoolUIDataContract.RADIANT_ARBITRUM.value,
        provider=provider,
        protocol_name=LendingPoolUIDataContract.RADIANT_ARBITRUM.name
    )
}

oracle_contract_interface = OracleContractInterface(
    address=config['AAVE_ARBITRUM_ORACLE_CONTRACT_ADDRESS'],
    provider=provider,
    protocol_name=LendingProtocol.AAVE_ARBITRUM.name
)
#############################################################################

# Custom contract interfaces #################################################
flash_liquidate_contract_interface = FlashLiquidateContractInterface(
    address=flash_liquidate_contract_address,
    abi=flash_liquidate_contract_abi,
    provider=provider,
)

#############################################################################
searcher = Searcher(
    lending_pool_interfaces=lending_pool_interfaces,
    ui_pool_data_interfaces=ui_pool_data_interfaces,
    oracle_interface=oracle_contract_interface,
    mongo_interface=db_interface,
    data_manager_queue=DATA_MANAGER_QUEUE,
    liquidations_queue=LIQUIDATIONS_QUEUE
)

data_manager = DataManager(db_interface=db_interface, data_manager_queue=DATA_MANAGER_QUEUE)

liquidator = Liquidator(
    flash_liquidate_contract_interface=flash_liquidate_contract_interface,
    liquidations_queue=LIQUIDATIONS_QUEUE
)

if __name__ == "__main__":
    pass
