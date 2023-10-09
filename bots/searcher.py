import pandas
from typing import Dict
from dotenv import dotenv_values, find_dotenv

from app_logger.logger import Logger
from db.mongo_db_interface import MongoInterface
from db.schemas.position_schema import UserAccountDataViewSchema, ReserveDataViewSchema, \
    UserAccountReservesDataViewSchema
from enums.enums import LendingProtocol, LendingPoolAddresses, LendingPoolUIDataContract, LendingPoolAddressesProvider
from sol.provider.provider import Provider
from sol.lending_pool_contract_interface import LendingPoolContractInterface
from sol.ui_pool_data_contract_interface import UIPoolDataContractInterface
from sol.oracle_contract_interface import OracleContractInterface

config = dotenv_values(dotenv_path=find_dotenv())
logger = Logger(section_name=__file__)

MAX_LIQUIDATION_PERCENT = 1.0
DEFAULT_LIQUIDATION_PERCENT = 0.5

# If account health factor is below this threshold, we will liquidate 100% of the position
CLOSE_FACTOR_HF_THRESHOLD = 0.95


class Searcher:
    """
    Searcher is a class that is responsible for searching for positions on lending protocols and updating the database

    :param lending_pool_interfaces: A dictionary of lending pool interfaces
    :param ui_pool_data_interfaces: A dictionary of UI pool data interfaces
    :param mongo_interface: A mongo interface
    """

    def __init__(
            self,
            lending_pool_interfaces: Dict[str, LendingPoolContractInterface],
            ui_pool_data_interfaces: Dict[str, UIPoolDataContractInterface],
            oracle_interface: OracleContractInterface,
            mongo_interface: MongoInterface
    ):
        self.lending_pool_interfaces = lending_pool_interfaces
        self.ui_pool_data_interfaces = ui_pool_data_interfaces
        self.oracle_interface = oracle_interface
        self.mongo_interface = mongo_interface

        logger_section_name = f"{__class__}"
        self.logger = Logger(section_name=logger_section_name)

    def get_protocol_events(self, protocol_name: str):
        """
        Get events from a lending protocol
        :param protocol_name:
        :return:
        """
        return self.lending_pool_interfaces[protocol_name].events

    def get_recent_protocol_borrows(self, protocol_name: str):
        """
        Get new borrows from a lending protocol
        :param protocol_name:
        :return:
        """
        return self.lending_pool_interfaces[protocol_name].recent_borrowers

    def get_user_account_data_from_recent_borrowers(self, protocol_name: str) -> pandas.DataFrame:
        """
        Get user account data from a lending protocol
        :param protocol_name:
        :return:
        """
        user_account_data_list = []
        for recent_borrower in self.lending_pool_interfaces[protocol_name].recent_borrowers:
            account_address = recent_borrower['account_address']
            account_data = self.lending_pool_interfaces[protocol_name].get_user_account_data(account_address)

            user_account_data = UserAccountDataViewSchema().load({
                "account_address": account_address,
                "total_collateral_eth": account_data[0],
                "total_debt_eth": account_data[1],
                "available_borrow_eth": account_data[2],
                "current_liquidation_threshold": account_data[3],
                "current_ltv": account_data[4],
                "health_factor": account_data[5],
                "protocol_name": protocol_name
            })
            self.logger.info(f"User account data: {user_account_data}")

            user_account_data_list.append(user_account_data)

        df = pandas.DataFrame.from_records(user_account_data_list)
        df = df.drop_duplicates(subset=['account_address', 'protocol_name'], keep='last')

        return df

    def get_user_reserve_data_from_recent_borrowers(self, protocol_name: str) -> pandas.DataFrame:
        """
        Get user reserve data from a lending protocol
        :param protocol_name:
        :return:
        """
        user_reserve_data_list = []
        for recent_borrower in self.lending_pool_interfaces[protocol_name].recent_borrowers:
            account_address = recent_borrower['account_address']
            reserve_data = self.ui_pool_data_interfaces[protocol_name].get_user_reserves_data(account_address)[0]

            account_reserves = []
            for reserve in reserve_data:
                user_reserve_data = {
                    "underlying_asset": reserve[0],
                    "scaled_a_token_balance": reserve[1],
                    "usage_as_collateral_enabled": reserve[2],
                    "stable_borrow_rate": reserve[3],
                    "scaled_variable_debt": reserve[4],
                    "principal_stable_debt": reserve[5],
                    "stable_borrow_last_update_timestamp": reserve[6]
                }
                self.logger.info(f"User reserve data: {user_reserve_data}")

                account_reserves.append(user_reserve_data)

            account_reserves_record = UserAccountReservesDataViewSchema().load({
                "account_address": account_address,
                "reserves": account_reserves,
                "protocol_name": protocol_name
            })
            user_reserve_data_list.append(account_reserves_record)

        df = pandas.DataFrame.from_records(user_reserve_data_list)
        df = df.drop_duplicates(subset=['account_address', 'protocol_name'], keep='last')

        return df

    def insert_updated_recent_borrow_data(self, protocol_name: str):
        """
        Insert updated recent borrow data into the database
        :param protocol_name:
        :return:
        """
        df = self.get_user_account_data_from_recent_borrowers(protocol_name)
        self.mongo_interface.insert_many('user_account_positions', df.to_dict('records'))

    def get_user_account_positions_from_mongo(self, protocol_name: str) -> pandas.DataFrame:
        """
        Get user account data from a lending protocol
        :param protocol_name:
        :return:
        """
        records = self.mongo_interface.find(collection='user_account_positions', query={'protocol_name': protocol_name})

        records_list = []
        for record in records:
            records_list.append(record)

        df = pandas.DataFrame.from_records(records_list)
        return df

    def check_for_liquidations(
            self,
            protocol_name: str,
            hf_threshold: float = 1.50,
            collateral_threshold: float = 1.00
    ):
        """
        Check for liquidations
        :param protocol_name:
        :return:
        """
        df_user_accounts: pandas.DataFrame = self.get_user_account_data_from_recent_borrowers(protocol_name)
        df_user_reserves: pandas.DataFrame = self.get_user_reserve_data_from_recent_borrowers(protocol_name)

        df = df_user_accounts.merge(
            df_user_reserves,
            on=['account_address', 'protocol_name'],
            how='inner'
        )

        liquidation_avail_positions = df[
            (df['health_factor'] < hf_threshold) & (df['total_collateral_eth'] > collateral_threshold)
            ]

        if liquidation_avail_positions.empty:
            logger.info("No positions available for liquidation")
        else:
            logger.info(f"Positions available for liquidation: {liquidation_avail_positions}")

        return liquidation_avail_positions

    def create_liquidation_params(
            self,
            protocol_name: str,
            positions: pandas.DataFrame
    ) -> pandas.DataFrame:
        """
        Create liquidation params
            - debt_to_cover = (scaled_variable_debt + principal_stable_debt) * (0.5 OR 1) --> Depending on HF
            - address collateralAsset, --> reserves with usage_as_collateral_enabled = true
            - address debtAsset, --> reserves with *debt_to_cover* > 0
            - address user, --> user account address
            - uint256 debtToCover, --> debt_to_cover
            - bool receiveAToken --> false

        :param protocol_name: Name of the protocol (ex. AAVE_ARBITRUM)
        :param positions: Dataframe of user positions to create the liquidation params from
        :return: Dataframe of containing liquidation params
        """
        liquidation_params = []
        account_addresses = positions['account_address'].tolist()
        for account_address in account_addresses:
            user_account_data = positions[
                (positions['account_address'] == account_address) &
                (positions['protocol_name'] == protocol_name)
                ]
            user_reserve_data = user_account_data['reserves']
            if user_account_data['health_factor'] < CLOSE_FACTOR_HF_THRESHOLD:
                collateral_close_factor = MAX_LIQUIDATION_PERCENT
            else:
                collateral_close_factor = DEFAULT_LIQUIDATION_PERCENT

            collateral_assets = []
            deb_assets = []
            for reserve in user_reserve_data:
                if reserve['usage_as_collateral_enabled'] is True:
                    collateral_assets.append({
                        "asset": reserve['underlying_asset'], "supplied": reserve['scaled_a_token_balance']
                    })
                if reserve['scaled_variable_debt'] > 0 or reserve['principal_stable_debt'] > 0:
                    debt = reserve['scaled_variable_debt'] + reserve['principal_stable_debt']
                    deb_assets.append(
                        {
                            "asset": reserve['underlying_asset'],
                            "debt": debt
                        }
                    )

            for collateral_asset in collateral_assets:
                for debt_asset in deb_assets:
                    collateral_price_usd = self.oracle_interface.get_asset_price_usd(collateral_asset['asset'])
                    collateral_value_usd = collateral_asset['supplied'] * collateral_price_usd

                    debt_price_usd = self.oracle_interface.get_asset_price_usd(debt_asset['asset'])
                    debt_value_usd = debt_asset['debt'] * debt_price_usd
                    if collateral_asset['asset'] == debt_asset['asset']:
                        debt_to_cover = debt_asset['debt'] * collateral_close_factor
                        liquidation_param = {
                            "collateral_asset": collateral_asset['asset'],
                            "debt_asset": debt_asset['asset'],
                            "user": account_address,
                            "debt_to_cover": debt_to_cover,
                            "receive_a_token": False,
                            "protocol_name": protocol_name
                        }
                        liquidation_params.append(liquidation_param)
                    elif debt_asset['debt'] > 0 and collateral_value_usd > debt_value_usd:
                        debt_to_cover = debt_asset['debt'] * collateral_close_factor
                        liquidation_param = {
                            "collateral_asset": collateral_asset['asset'],
                            "debt_asset": debt_asset['asset'],
                            "user": account_address,
                            "debt_to_cover": debt_to_cover,
                            "receive_a_token": False,
                            "protocol_name": protocol_name
                        }
                        liquidation_params.append(liquidation_param)

        liquidation_params_pd = pandas.DataFrame.from_records(liquidation_params)
        return liquidation_params_pd

    def live_search(self, protocol_name: str):
        """
        Live search for liquidations
        :param protocol_name:
        :return:
        """
        liquidation_avail_positions_df = self.check_for_liquidations(protocol_name)
        liquidation_params_df = self.create_liquidation_params(protocol_name, liquidation_avail_positions_df)

        df = liquidation_avail_positions_df.merge(
            liquidation_params_df,
            on=['account_address', 'protocol_name'],
            how='inner'
        )

        return df


def test_searcher():
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

    searcher = Searcher(
        lending_pool_interfaces=lending_pool_interfaces,
        ui_pool_data_interfaces=ui_pool_data_interfaces,
        oracle_interface=oracle_contract_interface,
        mongo_interface=db_interface
    )

    searcher.check_for_liquidations(LendingPoolAddressesProvider.AAVE_ARBITRUM.name)
    searcher.check_for_liquidations(LendingPoolAddressesProvider.RADIANT_ARBITRUM.name)


if __name__ == "__main__":
    test_searcher()
