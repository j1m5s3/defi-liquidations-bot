import os
from typing import Dict, Optional
from web3 import Web3
from web3.logs import DISCARD

from .contract_interface_base import ContractInterfaceBase


class FlashArbContractInterface(ContractInterfaceBase):
    def __init__(self, address: str, abi: list, provider):
        super().__init__(address, abi, provider)

    def check_single_dex_arbitrage(
            self,
            token0_address,
            token1_address,
            token2_address,
            pool_fee_1,
            pool_fee_2,
            pool_fee_3,
            amount_in,
    ) -> Dict:
        """
        :param token0_address: Address of token0
        :param token1_address: Address of token1
        :param token2_address: Address of token2
        :param pool_fee_1: Fee for pool 1 (token0 --> token1)
        :param pool_fee_2: Fee for pool 2 (token1 --> token2)
        :param pool_fee_3: Fee for pool 3 (token2 --> token0)
        :param amount_in: Amount of token0 to check for arbitrage
        :return: handler for function call

            Description:
                This function is used to check the quote for the given input amount.

                Parameters(.sol): address token0, uint256 feeTier1, address token1, uint256 feeTier2, address token2,
                uint256 amountIn,
                uint256 feeTier3,
        """

        token0 = Web3.to_checksum_address(token0_address)
        token1 = Web3.to_checksum_address(token1_address)
        token2 = Web3.to_checksum_address(token2_address)
        pool1 = int(pool_fee_1)
        pool2 = int(pool_fee_2)
        pool3 = int(pool_fee_3)
        amount = Web3.to_wei(amount_in, "ether")

        contract_function_handle = self.contract_functions().checkSingleDexArbitrage(
            token0,
            token1,
            token2,
            pool1,
            pool2,
            pool3,
            amount,
        )

        txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
        if txn_receipt["status"] == 0:
            raise Exception("Transaction failed")
        elif txn_receipt["status"] == 1:
            print("Transaction succeeded")

        event_logs = self.__get_event_logs(txn_receipt)

        return {"txn_receipt": txn_receipt, "event_logs": event_logs}

    def flash_loan_arbitrage(
            self,
            token0_address,
            token1_address,
            token2_address,
            pool_fee_1,
            pool_fee_2,
            pool_fee_3,
            amount_in,
    ) -> Optional[Dict]:

        token0 = Web3.to_checksum_address(token0_address)
        token1 = Web3.to_checksum_address(token1_address)
        token2 = Web3.to_checksum_address(token2_address)
        pool1 = int(pool_fee_1)
        pool2 = int(pool_fee_2)
        pool3 = int(pool_fee_3)
        amount = Web3.to_wei(amount_in, "ether")

        premium = amount_in * 0.0005
        amount_owed = amount_in + premium

        self.token_approve(token0)

        token_balance = self.get_token_balance(token0, wallet=True)
        if token_balance < amount_owed:
            raise Exception("Insufficient balance")

        self.token_transfer_from(token0, amount_owed)
        contract_function_handle = self.contract_functions().flashLoanArbitrage(
            token0,
            token1,
            token2,
            pool1,
            pool2,
            pool3,
            amount,
        )

        txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
        if txn_receipt["status"] == 0:
            raise Exception("Transaction failed")
        elif txn_receipt["status"] == 1:
            print("Transaction succeeded")

        event_logs = self.__get_event_logs(txn_receipt, event_name="Swap")

        return {"txn_receipt": txn_receipt, "event_logs": event_logs}

    def flash_loan_arbitrage_cross_dex(
            self,
            token0_address,
            amount_in,
            swap1_encoded,
            swap2_encoded,
            swap3_encoded,
            amount_in_wei=None,
            transfer_amount_to_contract=True,
    ) -> Dict:
        print(f"From process: {os.getpid()}")
        token0 = Web3.to_checksum_address(token0_address)

        if amount_in_wei is None:
            amount = Web3.to_wei(amount_in, "ether")
        else:
            amount = amount_in_wei

        swap1 = swap1_encoded
        swap2 = swap2_encoded
        swap3 = swap3_encoded

        premium = amount_in * 0.0005
        amount_owed = amount_in + premium

        if transfer_amount_to_contract:
            self.token_approve(token0)
            token_balance = self.get_token_balance(token0, wallet=True)
            if token_balance < amount_owed:
                raise Exception("Insufficient balance")

            self.token_transfer_from(token0, amount_owed)

        contract_function_handle = self.contract_functions().flashLoanTriArbitrageCrossDex(
            token0,
            amount,
            swap1,
            swap2,
            swap3,
        )

        try:
            print(f"Attempting flashLoanTriArbitrageCrossDex for {amount_in} with token0 {token0}", flush=True)
            print(f"Swap 1: {swap1}", flush=True)
            print(f"Swap 2: {swap2}", flush=True)
            print(f"Swap 3: {swap3}", flush=True)
            txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            return {"error": f"Transaction failed with error: {e}"}

        if txn_receipt["status"] == 0:
            raise Exception("Transaction failed")
        elif txn_receipt["status"] == 1:
            print("Transaction succeeded", flush=True)

        event_logs = self.__get_event_logs(txn_receipt, event_name="Swap")

        return {"txn_receipt": txn_receipt, "event_logs": event_logs}

    def uniswapv3_exact_input_single_quote(self, swap_encoded) -> Dict:

        swap = swap_encoded

        contract_function_handle = self.contract_functions().uniswapV3ExactInputSingleQuote(swap)

        txn_receipt = self.send_txn(contract_function_handle, signing_needed=True)
        if txn_receipt["status"] == 0:
            raise Exception("Transaction failed")
        elif txn_receipt["status"] == 1:
            print("Transaction succeeded")

        event_logs = self.__get_event_logs(txn_receipt, event_name="Quote")

        return {"txn_receipt": txn_receipt, "event_logs": event_logs}

    def get_sqrt_price_limit_from_input(self, sqrt_price_x96, liquidity, amount_in, zero_for_one, swap_type):
        contract_function_handle = self.contract_functions().getSqrtPriceLimitFromInput(
            sqrt_price_x96,
            liquidity,
            amount_in,
            zero_for_one,
        )
        try:
            sqrt_price_limit_x96 = contract_function_handle.call()
        except Exception as e:
            print(f"Error while getting sqrt_price_limit_x96 with params --> {e}")
            print(f"sqrt_price_x96: {sqrt_price_x96}")
            print(f"liquidity: {liquidity}")
            print(f"amount_out: {amount_in}")
            print(f"zero_for_one: {zero_for_one}")
            #raise Exception(f"Error while getting sqrt_price_limit_x96 --> {e}")
            return

        return sqrt_price_limit_x96

    def get_sqrt_price_limit_from_output(self, sqrt_price_x96, liquidity, amount_out, zero_for_one):
        contract_function_handle = self.contract_functions().getSqrtPriceLimitFromOutput(
            sqrt_price_x96,
            liquidity,
            amount_out,
            zero_for_one,
        )

        try:
            sqrt_price_limit_x96 = contract_function_handle.call()
        except Exception as e:
            print(f"Error while getting sqrt_price_limit_x96 with params --> {e}")
            print(f"sqrt_price_x96: {sqrt_price_x96}")
            print(f"liquidity: {liquidity}")
            print(f"amount_out: {amount_out}")
            print(f"zero_for_one: {zero_for_one}")
            #raise Exception(f"Error while getting sqrt_price_limit_x96 --> {e}")
            return

        return sqrt_price_limit_x96

    def get_arbitrage(self):
        return self.contract_functions().arbitrage().call()

    def __get_event_logs(self, txn_receipt, event_name="Arbitrage"):
        events = []

        event_handle = getattr(self.event_handle(), event_name)()

        logs = event_handle.get_logs(fromBlock=txn_receipt["blockNumber"])
        for log in logs:
            event_dict = {log.event: log.args}
            print(f"EVENT LOG -> {event_dict}", flush=True)
            events.append(event_dict)

        return events
