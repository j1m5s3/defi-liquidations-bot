# Provider for Web socket/JSON rpc
from web3 import Web3


class Provider:
    def __init__(self, wallet_address: str, wallet_private_key: str, https_url: str = None, ws_url: str = None):
        """
        :param wallet_address: type: str - Address of the wallet
        :param wallet_private_key: type: str - Private key of the wallet
        :param https_url: type: str - RPC url for https
        :param ws_url: type: str - RPC url for web socket

        Description:
            Provider class is used to create an entry point for the user to interact with the blockchain.
        """
        self.__wallet_address = wallet_address
        self.__wallet_private_key = wallet_private_key

        self.https_url = https_url
        self.ws_url = ws_url

        if https_url:
            self.w3 = Web3(Web3.HTTPProvider(self.https_url))
        elif ws_url:
            self.w3 = Web3(Web3.WebsocketProvider(self.ws_url))
        else:
            raise Exception("Please provide a valid RPC url.")

    def get_chain_id(self):
        return self.w3.eth.chain_id

    def get_nonce(self):
        return self.w3.eth.get_transaction_count(self.__wallet_address)

    def get_is_connected(self):
        return self.w3.is_connected

    def get_wallet_address(self):
        return self.__wallet_address

    def get_wallet_private_key(self):
        return self.__wallet_private_key
