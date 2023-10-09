import json
import pandas
from dotenv import dotenv_values, find_dotenv
from web3 import Web3

from enums.enums import (
    DexChain,
    EthChain,
    LendingProtocol,
    LendingPoolAddresses,
    LendingPoolAddressesProvider,
    LendingPoolUIDataContract
)
from db.mongo_db_interface import MongoInterface

from app_logger.logger import Logger

from db.schemas.position_schema import UserAccountDataViewSchema

from sol.provider.provider import Provider
from sol.contract_deployer import ContractDeployer
from sol.lending_pool_contract_interface import LendingPoolContractInterface
from sol.ui_pool_data_contract_interface import UIPoolDataContractInterface

config = dotenv_values(dotenv_path=find_dotenv())

CONFIGURED_PROTOCOLS = [LendingProtocol.AAVE_ARBITRUM, LendingProtocol.RADIANT_ARBITRUM]

logger = Logger(section_name=__file__)

if __name__ == "__main__":

    # TODO - Add mongo db interface to bot
    db_interface = MongoInterface(
        db_name=config["MONGO_DB_NAME"],
        connection_url=config["MONGO_CONNECTION_URL"]
    )

    try:
        # TODO - Add provider to bot
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

    user_position_data = []
    for lending_protocol in LendingProtocol:
        if lending_protocol in CONFIGURED_PROTOCOLS:
            for lending_pool_contract_address in LendingPoolAddresses:
                if lending_pool_contract_address.name == lending_protocol.name:
                    try:
                        # TODO - Add contract interface to bot
                        contract_interface = LendingPoolContractInterface(
                            address=lending_pool_contract_address.value,
                            provider=provider,
                            protocol_name=lending_protocol.name
                        )
                        logger.info(
                            f"{lending_protocol.name}_RECENT_BORROW_EVENTS: {contract_interface.events}"
                        )
                        logger.info(
                            f"{lending_protocol.name}_RECENT_BORROWERS: {contract_interface.recent_borrowers}"
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")

                    for recent_borrower in contract_interface.recent_borrowers:
                        return_data = contract_interface.get_user_account_data(recent_borrower['account_address'])

                        position_data = UserAccountDataViewSchema().load({
                            "account_address": recent_borrower['account_address'],
                            "total_collateral_eth": return_data[0],
                            "total_debt_eth": return_data[1],
                            "available_borrow_eth": return_data[2],
                            "current_liquidation_threshold": return_data[3],
                            "current_ltv": return_data[4],
                            "health_factor": return_data[5],
                            "protocol_name": lending_protocol.name
                        })
                        user_position_data.append(position_data)

    df = pandas.DataFrame.from_records(user_position_data)
    df = df.drop_duplicates(subset=['account_address', 'protocol_name'], keep='last')

    # Mongo DB check and insert
    insert_result = db_interface.insert_many('user_account_positions', df.to_dict('records'))

    liquidation_avail_positions = df.loc[df['health_factor'] < 1.00]
    liquidation_avail_addresses = set(liquidation_avail_positions['account_address'].to_list())

    reserve_data = []
    if liquidation_avail_positions.empty:
        logger.info("No positions available for liquidation")
    else:
        logger.info(f"Positions available for liquidation: {liquidation_avail_positions}")
        for address in liquidation_avail_addresses:
            positions = liquidation_avail_positions.loc[
                liquidation_avail_positions['account_address'] == address
            ].to_dict('records')

            for position in positions:
                logger.info(f"Position available for liquidation: {position}")
                if position['protocol_name'] == LendingProtocol.AAVE_ARBITRUM.name:
                    # TODO - Add contract interface to bot
                    contract_interface = UIPoolDataContractInterface(
                        address=LendingPoolUIDataContract.AAVE_ARBITRUM.value,
                        provider=provider,
                        protocol_name=position['protocol_name']
                    )
                    pool_address_provider_address = LendingPoolAddressesProvider.AAVE_ARBITRUM.value
                elif position['protocol_name'] == LendingProtocol.RADIANT_ARBITRUM.name:
                    contract_interface = UIPoolDataContractInterface(
                        address=LendingPoolUIDataContract.RADIANT_ARBITRUM.value,
                        provider=provider,
                        protocol_name=position['protocol_name']
                    )
                    pool_address_provider_address = LendingPoolAddressesProvider.RADIANT_ARBITRUM.value
                else:
                    logger.error(f"Protocol not supported: {position['protocol_name']}")
                    continue

                try:
                    return_data = contract_interface.get_user_reserves_data(
                        address_provider_address=pool_address_provider_address,
                        user_address=position['account_address']
                    )
                    logger.info(f"User reserve data: {return_data}")
                    reserve_data.append(return_data)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    logger.error(f"Failed to get user reserve data for {position['account_address']}")
                    continue

    logger.info("Done")
    pass
