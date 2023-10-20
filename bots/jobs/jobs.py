from multiprocessing import Queue
from dotenv import dotenv_values, find_dotenv

from app_logger.logger import Logger
from db.mongo_db_interface import MongoInterface
from enums.enums import LendingProtocol, SearchTypes, LendingPoolAddresses, LendingPoolUIDataContract
from bots.searcher import Searcher
from bots.data_manager import DataManager

from sol.flash_liquidate_contract_interface import FlashLiquidateContractInterface
from sol.lending_pool_contract_interface import LendingPoolContractInterface
from sol.oracle_contract_interface import OracleContractInterface
from sol.provider.provider import Provider
from sol.ui_pool_data_contract_interface import UIPoolDataContractInterface

logger = Logger(section_name=__name__)

config = dotenv_values(dotenv_path=find_dotenv())


def searcher_job(
        protocol: str,
        search_type: SearchTypes,
        dm_q: Queue,
        l_q: Queue,
        run_indefinitely: bool = False):
    """
    Searcher job


    :param protocol: Name of the protocol (ex. AAVE_ARBITRUM)
    :param search_type: Type of search (ex. SearchTypes.RECENT_BORROWS)
    :param dm_q: Data manager queue
    :param l_q: Liquidations queue
    :param run_indefinitely: Determines if the job should run indefinitely
    """
    logger.info(f"Starting searcher job for {protocol} from {search_type}")

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

    searcher = Searcher(
        lending_pool_interfaces=lending_pool_interfaces,
        ui_pool_data_interfaces=ui_pool_data_interfaces,
        oracle_interface=oracle_contract_interface,
        mongo_interface=db_interface,
        data_manager_queue=dm_q,
        liquidations_queue=l_q
    )
    searcher.live_search(protocol_name=protocol, search_type=search_type, run_indefinitely=run_indefinitely)


def data_manager_job(dm_q: Queue, run_indefinitely: bool = False):
    """
    Data manager job

    :param dm_q: Data manager queue
    :param run_indefinitely: Determines if the job should run indefinitely
    """
    logger.info("Starting data manager job")
    db_interface = MongoInterface(
        db_name=config["MONGO_DB_NAME"],
        connection_url=config["MONGO_CONNECTION_URL"]
    )

    data_manager = DataManager(db_interface=db_interface, data_manager_queue=dm_q)
    data_manager.monitor_queue(run_indefinitely=run_indefinitely)
