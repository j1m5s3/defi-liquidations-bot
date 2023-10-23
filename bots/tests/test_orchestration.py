import time
from threading import Thread

from enums.enums import LendingProtocol, SearchTypes
from bots.jobs.jobs import data_manager_job, searcher_job, liquidator_job


def test_orchestrate_bots(sets_of_bots: int = 1):
    """
    Orchestrate bots
    :return:
    """

    # Searcher
    live_search_worker = searcher_job
    # DataManager
    data_manager_worker = data_manager_job
    # Liquidator
    liquidator_worker = liquidator_job

    for sets in range(sets_of_bots):
        # # Start processes
        # live_search_process_aave_rb = Thread(
        #     target=live_search_worker,
        #     args=(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.RECENT_BORROWS, True)
        # )
        # live_search_process_aave_fr = Thread(
        #     target=live_search_worker,
        #     args=(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.FROM_RECORDS, True)
        # )
        # live_search_process_radiant_rb = Thread(
        #     target=live_search_worker,
        #     args=(LendingProtocol.RADIANT_ARBITRUM.name, SearchTypes.RECENT_BORROWS, True)
        # )
        # live_search_process_radiant_fr = Thread(
        #     target=live_search_worker,
        #     args=(LendingProtocol.RADIANT_ARBITRUM.name, SearchTypes.FROM_RECORDS, True)
        # )
        # data_manager_process = Thread(target=data_manager_worker, args=(True,))
        liquidator_process = Thread(target=liquidator_worker, args=(True,))

        # Start processes
        # live_search_process_aave_rb.start()
        # live_search_process_aave_fr.start()
        # live_search_process_radiant_rb.start()
        # live_search_process_radiant_fr.start()
        # data_manager_process.start()

        liquidator_process.start()

        # live_search_process_aave_rb.join()
        # live_search_process_aave_fr.join()
        # live_search_process_radiant_rb.join()
        # live_search_process_radiant_fr.join()
        # data_manager_process.join()
        liquidator_process.join()

    return


if __name__ == '__main__':
    test_orchestrate_bots(sets_of_bots=1)
