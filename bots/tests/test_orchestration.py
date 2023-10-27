import argparse
import time
from threading import Thread

from enums.enums import LendingProtocol, SearchTypes
from bots.jobs.jobs import data_manager_job, searcher_job, liquidator_job


def test_orchestrate_bots(
        sets_of_bots: int = 1, 
        run_indefinitely: bool = False,
        run_searcher: bool = False,
        run_data_manager: bool = False,
        run_liquidator: bool = False
):
    """
    Orchestrate bots

    :param sets_of_bots: Number of sets of bots to run
    :param run_indefinitely: Determines if the job should run indefinitely
    :param run_searcher: Determines if the searcher job should run
    :param run_data_manager: Determines if the data manager job should run
    :param run_liquidator: Determines if the liquidator job should run
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
        if run_searcher:
            live_search_process_aave_rb = Thread(
                target=live_search_worker,
                args=(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.RECENT_BORROWS, run_indefinitely)
            )
            live_search_process_aave_fr = Thread(
                target=live_search_worker,
                args=(LendingProtocol.AAVE_ARBITRUM.name, SearchTypes.FROM_RECORDS, run_indefinitely)
            )
            live_search_process_radiant_rb = Thread(
                target=live_search_worker,
                args=(LendingProtocol.RADIANT_ARBITRUM.name, SearchTypes.RECENT_BORROWS, run_indefinitely)
            )
            live_search_process_radiant_fr = Thread(
                target=live_search_worker,
                args=(LendingProtocol.RADIANT_ARBITRUM.name, SearchTypes.FROM_RECORDS, run_indefinitely)
            )

            # Start threads
            live_search_process_aave_rb.start()
            live_search_process_aave_fr.start()
            live_search_process_radiant_rb.start()
            live_search_process_radiant_fr.start()

            # Wait for threads to finish
            live_search_process_aave_rb.join()
            live_search_process_aave_fr.join()
            live_search_process_radiant_rb.join()
            live_search_process_radiant_fr.join()
        
        if run_data_manager:
            data_manager_process = Thread(target=data_manager_worker, args=(run_indefinitely,))
            data_manager_process.start()
            
            # Wait for threads to finish
            data_manager_process.join()
        
        if run_liquidator:
            liquidator_process = Thread(target=liquidator_worker, args=(run_indefinitely,))
            liquidator_process.start()
            
            # Wait for threads to finish
            liquidator_process.join()
    return


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="A simple script to test bot orchestration")
    parser.add_argument("--runs", action='store_true', default=False, help="Run Searcher")
    parser.add_argument("--rund", action='store_true', default=False, help="Run DataManager")
    parser.add_argument("--runl", action='store_true', default=False, help="Run Liquidator")
    parser.add_argument("--sets", type=int, default=1, help="Number of sets of bots to run")
    parser.add_argument("--indef", action='store_true', default=False, help="Run bots indefinitely")

    args = parser.parse_args()
    runs = args.runs
    rund = args.rund
    runl = args.runl
    sets = args.sets
    indef = args.indef

    test_orchestrate_bots(
        sets_of_bots=1,
        run_indefinitely=indef,
        run_searcher=runs,
        run_data_manager=rund,
        run_liquidator=runl
    )
