from enums.enums import LendingPoolAddressesProvider, SearchTypes


from bots.tests.interfaces import searcher


def test_searcher():
    """
    Test searcher
    :return:
    """

    #searcher.check_for_liquidations(LendingPoolAddressesProvider.AAVE_ARBITRUM.name)
    #searcher.check_for_liquidations(LendingPoolAddressesProvider.RADIANT_ARBITRUM.name)

    # searcher.live_search(
    #     LendingPoolAddressesProvider.AAVE_ARBITRUM.name,
    #     SearchTypes.RECENT_BORROWS
    # )
    searcher.live_search(
        LendingPoolAddressesProvider.RADIANT_ARBITRUM.name,
        SearchTypes.FROM_RECORDS
    )


if __name__ == "__main__":
    test_searcher()
