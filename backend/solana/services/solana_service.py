import logging
import requests
import json

logger = logging.getLogger('solana')


class SolanaService:
    RPC_URL = "https://api.mainnet-beta.solana.com"

    def _rpc_call(self, method, params):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        try:
            response = requests.post(self.RPC_URL, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Solana RPC timed out for method=%s", method)
            return {"error": "Solana RPC request timed out"}
        except requests.exceptions.RequestException as e:
            logger.error("Solana RPC request failed for method=%s: %s", method, e)
            return {"error": str(e)}

    def get_wallet_info(self, address):
        balance_data = self._rpc_call("getBalance", [address])
        signatures_data = self._rpc_call("getSignaturesForAddress", [address, {"limit": 10}])

        return {
            "balance": balance_data.get('result', {}).get('value', 0),
            "signatures": signatures_data.get('result', [])
        }

    def get_transaction_details(self, signature):
        tx_data = self._rpc_call("getTransaction", [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}])
        return tx_data.get('result')
