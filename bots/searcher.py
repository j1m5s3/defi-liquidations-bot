import pandas
from typing import Dict
from dotenv import dotenv_values, find_dotenv

from app_logger.logger import Logger
from db.mongo_db_interface import MongoInterface
from db.schemas.position_schema import UserAccountDataViewSchema, ReserveDataViewSchema, \
    UserAccountReservesDataViewSchema
from enums.enums import SearchTypes
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

    def get_user_account_data_from_protocol(
            self,
            protocol_name: str,
            search_type: SearchTypes
    ) -> pandas.DataFrame:
        """
        Get user account data from a lending protocol

        :param protocol_name:
        :param search_type:
        :return:
        """

        if search_type == SearchTypes.RECENT_BORROWS:
            # Refresh the borrows data
            self.lending_pool_interfaces[protocol_name].refresh_contract_data()
            accounts = self.lending_pool_interfaces[protocol_name].recent_borrowers
        elif search_type == SearchTypes.FROM_RECORDS:
            accounts = self.get_user_account_positions_from_mongo(protocol_name).to_records()
        else:
            raise ValueError(f"Invalid search type: {search_type}")

        user_account_data_list = []
        for account in accounts:
            account_address = account['account_address']
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
            self.logger.info(f"User account data - {search_type.name}: {user_account_data}")

            user_account_data_list.append(user_account_data)

        df = pandas.DataFrame.from_records(user_account_data_list)
        df = df.drop_duplicates(subset=['account_address', 'protocol_name'], keep='last')

        return df

    def get_user_reserve_data_from_protocol(
            self,
            protocol_name: str,
            search_type: SearchTypes
    ) -> pandas.DataFrame:
        """
        Get user reserve data from a lending protocol

        :param protocol_name:
        :param search_type:
        :return:
        """

        if search_type == SearchTypes.RECENT_BORROWS:
            accounts = self.lending_pool_interfaces[protocol_name].recent_borrowers
        elif search_type == SearchTypes.FROM_RECORDS:
            accounts = self.get_user_account_positions_from_mongo(protocol_name).to_records()
        else:
            raise ValueError(f"Invalid search type: {search_type}")

        user_reserve_data_list = []
        for account in accounts:
            account_address = account['account_address']
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
                self.logger.info(f"User reserve data - {search_type.name}: {user_reserve_data}")

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

    def insert_updated_account_data(self, protocol_name: str):
        """
        Insert updated recent borrow data into the database
        :param protocol_name:
        :return:
        """
        df = self.get_user_account_data_from_protocol(protocol_name, SearchTypes.FROM_RECORDS)
        self.mongo_interface.insert_many('user_account_positions', df.to_dict('records'))

    def get_user_account_positions_from_mongo(self, protocol_name: str) -> pandas.DataFrame:
        """
        Get user account data from a lending protocol
        :param protocol_name:
        :return:
        """
        records = self.mongo_interface.find(collection='user_account_positions', query={'protocol_name': protocol_name})

        records_list = list(records)

        df = pandas.DataFrame.from_records(records_list)
        return df

    def check_for_liquidations(
            self,
            protocol_name: str,
            search_type: SearchTypes = SearchTypes.RECENT_BORROWS,
            hf_threshold: float = 1.80,
            collateral_threshold: float = 1.00,
    ) -> pandas.DataFrame:
        """
        Check for liquidations

        :param protocol_name: Protocol name to check for liquidations
        :param collateral_threshold: Amount of collateral to check for liquidations
        :param hf_threshold: Health factor threshold to check for liquidations
        :param search_type: Type of search to perform
        :return: Dataframe of positions available for liquidation
        """

        df_user_accounts: pandas.DataFrame = self.get_user_account_data_from_protocol(protocol_name, search_type)
        df_user_reserves: pandas.DataFrame = self.get_user_reserve_data_from_protocol(protocol_name, search_type)

        df = df_user_accounts.merge(
            df_user_reserves,
            on=['account_address', 'protocol_name'],
            how='inner'
        )

        # liquidation_avail_positions = df[
        #     (df['health_factor'] < hf_threshold) & (df['total_collateral_eth'] > collateral_threshold)
        #     ]

        liquidation_avail_positions = df[(df['health_factor'] < hf_threshold)]

        if liquidation_avail_positions.empty:
            logger.info("No positions available for liquidation")
        else:
            logger.info(f"Positions available for liquidation: {liquidation_avail_positions}")

        return liquidation_avail_positions

    def to_liquidation_params(self, user_account_data: pandas.DataFrame) -> pandas.DataFrame:
        """
        Apply liquidation parameters to user account data

        :param user_account_data:
        :return:
        """
        liquidation_params = []

        account_address = user_account_data['account_address']
        protocol_name = user_account_data['protocol_name']

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
            collateral_price_usd = self.oracle_interface.get_asset_price_usd(collateral_asset['asset'])
            collateral_value_usd = collateral_asset['supplied'] * collateral_price_usd
            for debt_asset in deb_assets:
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

    def create_liquidation_params(
            self,
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

        :param positions: Dataframe of user positions to create the liquidation params from
        :return: Dataframe of containing liquidation params
        """

        liquidation_params = positions.apply(
            self.to_liquidation_params, axis=1
        )
        liquidation_params_df = pandas.concat(liquidation_params.to_list())

        return liquidation_params_df

    def live_search(
            self,
            protocol_name: str,
            search_type: SearchTypes
    ) -> pandas.DataFrame:
        """
        Live search for liquidations return parameters for liquidations

        :param protocol_name: Name of the protocol to search for liquidations on
        :param search_type: Type of search to perform
        :return: Dataframe of liquidation params
        """
        self.logger.info(f"Searching for liquidations on {protocol_name} or search type {search_type.name}")

        liquidation_avail_positions_df = self.check_for_liquidations(protocol_name, search_type)
        liquidation_params_df = self.create_liquidation_params(liquidation_avail_positions_df)

        return liquidation_params_df



