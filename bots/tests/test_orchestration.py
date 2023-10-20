import time
from threading import Thread
from multiprocessing import Process, Queue

from enums.enums import LendingProtocol, SearchTypes
from bots.jobs.jobs import data_manager_job, searcher_job


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
    # liquidator_worker = liquidator.liquidate

    dm_q = Queue()
    l_q = Queue()

    for sets in range(sets_of_bots):
        # searcher.live_search(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.RECENT_BORROWS, run_indefinitely=False)
        # data_manager.monitor_queue(run_indefinitely=False)

        # Start processes
        live_search_process_aave_rb = Thread(
            target=live_search_worker,
            args=(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.RECENT_BORROWS, dm_q, l_q)
        )
        # live_search_process_aave_fr = Process(
        #     target=live_search_worker,
        #     args=(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.FROM_RECORDS)
        # )
        # live_search_process_radiant_rb = Process(
        #     target=live_search_worker,
        #     args=(LendingProtocol.RADIANT_ARBITRUM.name, SearchTypes.RECENT_BORROWS)
        # )
        # live_search_process_radiant_fr = Process(
        #     target=live_search_worker,
        #     args=(LendingProtocol.RADIANT_ARBITRUM.name, SearchTypes.FROM_RECORDS)
        # )
        data_manager_process = Thread(target=data_manager_worker, args=(dm_q,))
        #liquidator_process = Process(target=liquidator_worker)

        # Start processes
        live_search_process_aave_rb.start()
        #live_search_process_aave_fr.start()
        # live_search_process_radiant_rb.start()
        # live_search_process_radiant_fr.start()
        data_manager_process.start()

        #liquidator_process.start()

        live_search_process_aave_rb.join()
        # live_search_process_aave_fr.join()
        # live_search_process_radiant_rb.join()
        # live_search_process_radiant_fr.join()
        data_manager_process.join()

    return


if __name__ == '__main__':
    test_orchestrate_bots(sets_of_bots=2)
