"""Deploy ConsentLedger to a running local Anvil node."""
import json
from pathlib import Path
from backend import config
from backend.chain.client import ABI_PATH, DEPLOY_PATH

def deploy() -> str:
    try: from web3 import Web3
    except ImportError as exc: raise RuntimeError("Install web3 to deploy the contract") from exc
    if not ABI_PATH.is_file(): raise FileNotFoundError(f"Compile ConsentLedger first: {ABI_PATH}")
    w3=Web3(Web3.HTTPProvider(config.RPC_URL,request_kwargs={"timeout":3}))
    if not w3.is_connected(): raise RuntimeError(f"Cannot connect to Anvil at {config.RPC_URL}")
    artifact=json.loads(ABI_PATH.read_text(encoding="utf-8")); factory=w3.eth.contract(abi=artifact["abi"],bytecode=artifact["bytecode"]["object"])
    tx=factory.constructor().transact({"from":w3.eth.accounts[0]}); receipt=w3.eth.wait_for_transaction_receipt(tx,timeout=30)
    if receipt.status!=1 or not receipt.contractAddress: raise RuntimeError("ConsentLedger deployment failed")
    DEPLOY_PATH.parent.mkdir(parents=True,exist_ok=True); DEPLOY_PATH.write_text(json.dumps({"address":receipt.contractAddress},indent=2),encoding="utf-8")
    return receipt.contractAddress
if __name__=="__main__": print("deployed",deploy())
