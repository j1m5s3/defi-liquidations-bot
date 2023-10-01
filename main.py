import json
from dotenv import dotenv_values, find_dotenv

from enums.enums import DexChain, EthChain, LendingProtocol, LendingPoolAddresses

from app_logger.logger import Logger

from sol.provider.provider import Provider
from sol.contract_deployer import ContractDeployer
from sol.lending_pool_contract_interface import LendingPoolContractInterface

config = dotenv_values(dotenv_path=find_dotenv())

CONFIGURED_PROTOCOLS = [LendingProtocol.AAVE_ARBITRUM, LendingProtocol.RADIANT_ARBITRUM]

logger = Logger(section_name=__name__)

if __name__ == "__main__":

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

    for lending_protocol in LendingProtocol:
        if lending_protocol in CONFIGURED_PROTOCOLS:
            for lending_pool_contract_address in LendingPoolAddresses:
                if lending_pool_contract_address.name == lending_protocol.name:
                    try:
                        contract_interface = LendingPoolContractInterface(
                            address=lending_pool_contract_address.value,
                            provider=provider,
                            protocol_name=lending_protocol.name
                        )
                        logger.info(f"{lending_protocol.name}: {contract_interface.events}")
                    except Exception as e:
                        logger.error(f"Error: {e}")
    pass
