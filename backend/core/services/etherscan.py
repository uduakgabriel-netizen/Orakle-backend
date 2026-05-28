import logging
import requests
import time
from django.conf import settings

logger = logging.getLogger('core')


class EtherscanService:
    BASE_URL = "https://api.etherscan.io/v2/api"
    MAX_RETRIES = 2
    INITIAL_BACKOFF = 0.5  # seconds
    TIMEOUT = 10  # seconds

    def __init__(self):
        self.api_key = settings.ETHERSCAN_API_KEY
        if not self.api_key:
            logger.warning("EtherscanService initialized without API key.")

    def _get(self, params):
        params['apikey'] = self.api_key
        params['chainid'] = 1
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning("Etherscan request timed out for action=%s. Retrying in %s seconds (attempt %d/%d)", 
                                 params.get('action'), wait_time, attempt + 1, self.MAX_RETRIES)
                    time.sleep(wait_time)
                else:
                    logger.error("Etherscan request timed out after %d attempts for action=%s", self.MAX_RETRIES, params.get('action'))
                    return {"status": "0", "message": "Etherscan request timed out after retries"}
            except requests.exceptions.RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning("Etherscan request failed for action=%s: %s. Retrying in %s seconds (attempt %d/%d)", 
                                 params.get('action'), str(e), wait_time, attempt + 1, self.MAX_RETRIES)
                    time.sleep(wait_time)
                else:
                    logger.error("Etherscan request failed after %d attempts for action=%s: %s", self.MAX_RETRIES, params.get('action'), e)
                    return {"status": "0", "message": f"Etherscan request failed: {e}"}

    def get_wallet_transactions(self, address):
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': 100,
            'sort': 'desc'
        }
        return self._get(params)

    def get_contract_source_code(self, address):
        params = {
            'module': 'contract',
            'action': 'getsourcecode',
            'address': address
        }
        return self._get(params)

    def get_transaction_receipt(self, tx_hash):
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionByHash',
            'txhash': tx_hash
        }
        return self._get(params)

    def get_implementation_abi(self, implementation_address):
        """Fetch ABI for a proxy's implementation contract."""
        params = {
            'module': 'contract',
            'action': 'getabi',
            'address': implementation_address
        }
        result = self._get(params)
        if result.get('status') == '1':
            return result.get('result', '')
        logger.info("Could not fetch implementation ABI for %s", implementation_address)
        return None
