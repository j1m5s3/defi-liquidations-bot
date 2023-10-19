
from app_logger.logger import Logger
from enums.enums import LendingProtocol, SearchTypes
from bots.searcher import Searcher
from bots.data_manager import DataManager

logger = Logger(section_name=__name__)


def searcher_job(protocol: str, search_type: SearchTypes, searcher: Searcher, run_indefinitely: bool = False):
    """
    Searcher job

    :param protocol: Name of the protocol (ex. AAVE_ARBITRUM)
    :param search_type: Type of search (ex. SearchTypes.RECENT_BORROWS)
    :param searcher: Class instance of Searcher
    :param run_indefinitely: Determines if the job should run indefinitely
    """
    logger.info(f"Starting searcher job for {protocol} from {search_type}")
    searcher.live_search(protocol_name=protocol, search_type=search_type, run_indefinitely=run_indefinitely)


def data_manager_job(data_manager: DataManager, run_indefinitely: bool = False):
    """
    Data manager job
    """
    logger.info("Starting data manager job")
    data_manager.monitor_queue(run_indefinitely=run_indefinitely)

