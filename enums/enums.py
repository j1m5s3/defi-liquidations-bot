from enum import Enum
from dotenv import dotenv_values, find_dotenv

config = dotenv_values(dotenv_path=find_dotenv())


class DexChain(Enum):
    UNI_ARBITRUM = 1
    SUSHI_ARBITRUM = 2
    UNI_OPTIMISM = 3
    SUSHI_OPTIMISM = 4
    UNI_MAIN = 5
    SUSHI_MAIN = 6


class EthChain(Enum):
    ARBITRUM = 1
    OPTIMISM = 2
    MAIN = 3


class LendingProtocol(Enum):
    AAVE_ARBITRUM = 1
    COMPOUND_ARBITRUM = 2
    RADIANT_ARBITRUM = 3


class LendingPoolAddresses(Enum):
    AAVE_ARBITRUM = config["AAVE_POOL_CONTRACT_ADDRESS_ARBITRUM"]
    COMPOUND_ARBITRUM = None
    RADIANT_ARBITRUM = config["RADIANT_POOL_CONTRACT_ADDRESS_ARBITRUM"]


class LendingPoolAddressesProvider(Enum):
    AAVE_ARBITRUM = config["AAVE_ARBITRUM_POOL_CONTRACT_ADDRESS_PROVIDER"]
    COMPOUND_ARBITRUM = None
    RADIANT_ARBITRUM = config["RADIANT_ARBITRUM_POOL_CONTRACT_ADDRESS_PROVIDER"]


class LendingPoolUIDataContract(Enum):
    AAVE_ARBITRUM = config["AAVE_UI_POOL_DATA_CONTRACT_ADDRESS_ARBITRUM"]
    COMPOUND_ARBITRUM = None
    RADIANT_ARBITRUM = config["RADIANT_UI_POOL_DATA_CONTRACT_ADDRESS_ARBITRUM"]


class SearchTypes(Enum):
    RECENT_BORROWS = 1
    FROM_RECORDS = 2
