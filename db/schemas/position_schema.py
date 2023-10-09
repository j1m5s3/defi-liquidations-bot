from web3 import Web3
from marshmallow import Schema, fields, validate, pre_load, EXCLUDE



class UserAccountDataViewSchema(Schema):
    """
    Schema for Account Pool position. Derived from AAVE view function return values
    """
    account_address = fields.Str(required=True, validate=validate.Length(min=42, max=42))  # address
    total_collateral_eth = fields.Float(required=True)  # uint256
    total_debt_eth = fields.Float(required=True)  # uint256
    available_borrow_eth = fields.Float(required=True)  # uint256
    current_liquidation_threshold = fields.Float(required=True)  # uint256
    current_ltv = fields.Float(required=True)  # uint256
    health_factor = fields.Float(required=True)  # uint256
    protocol_name = fields.Str(required=True)  # str

    @pre_load
    def process_input(self, data, **kwargs):
        for key in data.keys():
            if key in ['total_collateral_eth', 'total_debt_eth', 'available_borrow_eth',
                       'current_liquidation_threshold', 'current_ltv', 'health_factor']:
                data[key] = Web3.from_wei(data[key], 'ether')

        return data


class ReserveDataViewSchema(Schema):
    underlying_asset = fields.Str(required=True)  # address
    scaled_a_token_balance = fields.Float(required=True)  # uint256
    usage_as_collateral_enabled = fields.Bool(required=True)  # bool
    stable_borrow_rate = fields.Float(required=True)  # uint256
    scaled_variable_debt = fields.Float(required=True)  # uint256
    principal_stable_debt = fields.Float(required=True)  # uint256
    stable_borrow_last_update_timestamp = fields.Float(required=True)  # uint256

    @pre_load
    def process_input(self, data, **kwargs):
        for key in data.keys():
            if key in ['scaled_a_token_balance', 'stable_borrow_rate', 'scaled_variable_debt',
                       'principal_stable_debt', 'stable_borrow_last_update_timestamp']:
                data[key] = Web3.from_wei(data[key], 'ether')

        return data


class UserAccountReservesDataViewSchema(Schema):
    """
    Schema for Account Pool position including reserves. Derived from AAVE view function return values
    """
    account_address = fields.Str(required=True, validate=validate.Length(min=42, max=42)) # address
    reserves = fields.Nested(ReserveDataViewSchema, many=True)
    protocol_name = fields.Str(required=True)  # str


class PositionRecordSchema(UserAccountDataViewSchema, UserAccountReservesDataViewSchema):
    """
    Schema for Account Pool position including reserves to be stored in DB
    """


class BorrowEvent(Schema):
    """
    Schema for desired data from a Borrow event from the Pool contract view function call
    """
    account_address = fields.Str(required=True, validate=validate.Length(min=42, max=42))

    @pre_load
    def process_input(self, data, **kwargs):
        if 'user' in data:
            data['account_address'] = data['user']
        return data

    class Meta:
        unknown = EXCLUDE
