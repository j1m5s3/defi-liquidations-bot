import json
import argparse
from alive_progress import alive_bar
from dotenv import dotenv_values, find_dotenv

from app_logger.logger import Logger

from sol.provider.provider import Provider
from sol.contract_deployer import ContractDeployer

config = dotenv_values(dotenv_path=find_dotenv())

logger = Logger(section_name=__file__)


def compile_and_deploy_contract(
        contract_name: str = "FlashArb",
        provider: Provider = None,
        constructor_args=None
):
    # Construct web3 provider

    if provider is None:
        provider = Provider(
            wallet_address=config["WALLET_ADDRESS"],
            wallet_private_key=config["WALLET_PRIVATE_KEY"],
            https_url=None,
            ws_url=config["ALCHEMY_WSS_RPC_URL_GOERLI"]
        )

    # Construct contract deployer
    contract_id = ":" + contract_name

    contract_deployer = ContractDeployer(
        provider=provider,
        contract_source_path=f"./sol/contracts/{contract_name}.sol",
        contract_name=contract_id,
        constructor_args=constructor_args,
    )

    # Deploy contract
    txn_receipt = contract_deployer.deploy()

    if txn_receipt:
        contract_address = txn_receipt["contract_address"]
        abi = txn_receipt["abi"]
        filename = f"{contract_name}.json"
        print(f"Saving compiled contract info to {filename}...")
        export_path = f"./sol/contracts/{filename}"
        with open(export_path, "w") as f:
            json.dump({"contract_address": contract_address, "abi": abi}, f)
            print(f"Compiled contract info saved to {contract_name}.json...")
    else:
        raise Exception("txn_receipt is None")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple script to compile and deploy a contract")
    parser.add_argument("--test", action='store_true', default=True, help="Testnet deploy")
    parser.add_argument("--main", action='store_true', default=False, help="Mainnet deploy")

    args = parser.parse_args()

    # Construct web3 provider
    if args.test:
        logger.info("Deploying to testnet...")
        provider = Provider(
            wallet_address=config["WALLET_ADDRESS"],
            wallet_private_key=config["WALLET_PRIVATE_KEY"],
            https_url=None,
            ws_url=config["ALCHEMY_WSS_RPC_URL_GOERLI"]
        )
        constructor_args = {"_addressProvider": config["AAVE_GOERLI_POOL_ADDRESS_PROVIDER"]}
    elif args.main:
        pass

    with alive_bar(monitor=None, stats=None, title="Compiling and deploying contract..."):
        compile_and_deploy_contract(
            contract_name="FlashLiquidate",
            provider=provider,
            constructor_args=constructor_args
        )

