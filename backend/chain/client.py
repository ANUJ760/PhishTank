"""Web3 client for the local Foundry deployment."""
from __future__ import annotations
import json
from pathlib import Path
from backend import config

ABI_PATH=Path("contracts/out/ConsentLedger.sol/ConsentLedger.json")
DEPLOY_PATH=Path("data/deployment.json")
class ChainError(RuntimeError): pass

class Chain:
    def __init__(self):
        try: from web3 import Web3
        except ImportError as exc: raise ChainError("Install web3 to use the consent ledger") from exc
        if not ABI_PATH.is_file() or not DEPLOY_PATH.is_file(): raise ChainError("Contract is not compiled or deployed")
        try:
            artifact=json.loads(ABI_PATH.read_text(encoding="utf-8")); address=json.loads(DEPLOY_PATH.read_text(encoding="utf-8"))["address"]
            self.w3=Web3(Web3.HTTPProvider(config.RPC_URL,request_kwargs={"timeout":3}))
            if not self.w3.is_connected(): raise ChainError("Anvil RPC is unavailable")
            self.c=self.w3.eth.contract(address=address,abi=artifact["abi"]); self.accounts=self.w3.eth.accounts
        except ChainError: raise
        except Exception as exc: raise ChainError(f"Cannot load the local contract: {exc}") from exc
    def addr(self,name: str) -> str:
        if name not in config.ACCOUNT_INDEX: raise ChainError(f"no wallet configured for {name}")
        index=config.ACCOUNT_INDEX[name]
        if index>=len(self.accounts): raise ChainError(f"Anvil account for {name} is unavailable")
        return self.accounts[index]
    def _send(self,fn,sender: str) -> str:
        try:
            tx=fn.transact({"from":self.addr(sender)}); receipt=self.w3.eth.wait_for_transaction_receipt(tx,timeout=15)
            if receipt.status!=1: raise ChainError("Ledger transaction failed")
            from web3 import Web3
            return Web3.to_hex(tx)
        except ChainError: raise
        except Exception as exc: raise ChainError(str(exc)) from exc
    def register_rule(self,rule_hash: bytes,owner: str) -> str: return self._send(self.c.functions.registerRule(rule_hash,self.addr(owner)),"Coordinator")
    def approve(self,rule_hash: bytes,opt_hash: bytes,as_user: str) -> str: return self._send(self.c.functions.approveRelaxation(rule_hash,opt_hash),as_user)
    def is_approved(self,rule_hash: bytes,opt_hash: bytes) -> bool: return bool(self.c.functions.approved(rule_hash,opt_hash).call())
    def anchor(self,sched_hash: bytes,version: int) -> str: return self._send(self.c.functions.anchorSchedule(sched_hash,version),"Coordinator")
    def is_anchored(self,sched_hash: bytes) -> bool: return bool(self.c.functions.anchored(sched_hash).call())
    def events(self) -> list[dict]:
        out=[]
        from web3 import Web3
        for name in ("RuleRegistered","RelaxationApproved","ScheduleAnchored"):
            for event in getattr(self.c.events,name)().get_logs(from_block=0):
                args={k:(Web3.to_hex(v) if isinstance(v,(bytes,bytearray)) else v) for k,v in event["args"].items()}
                out.append({"event":name,"block":event["blockNumber"],"idx":event["logIndex"],"args":args})
        return sorted(out,key=lambda e:(e["block"],e["idx"]))
