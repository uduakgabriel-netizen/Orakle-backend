import logging
from core.services.etherscan import EtherscanService
from ..models import TransactionAnalysis

logger = logging.getLogger('transactions')


class TransactionTranslatorService:
    def __init__(self):
        self.etherscan = EtherscanService()

    def translate(self, tx_hash):
        tx_data = self.etherscan.get_transaction_receipt(tx_hash)

        if not tx_data or 'result' not in tx_data or tx_data['result'] is None:
            logger.error("Transaction not found on Etherscan: %s", tx_hash)
            return {"success": False, "error": "Transaction not found"}

        result = tx_data['result']

        tx_type = self._classify_type(result)
        summary = self._generate_summary(result, tx_type)

        analysis = TransactionAnalysis.objects.create(
            tx_hash=tx_hash,
            parsed_data=result,
            interpretation=summary
        )

        logger.info("Transaction analysis saved: id=%d hash=%s type=%s", analysis.id, tx_hash, tx_type)

        return {
            "success": True,
            "data": {
                "type": tx_type,
                "from": result.get('from'),
                "to": result.get('to'),
                "value": str(int(result.get('value', '0x0'), 16) / 10**18) + " ETH",
                "summary": summary
            }
        }

    def _classify_type(self, tx):
        input_data = tx.get('input', '0x')
        if input_data == '0x' or input_data == '0x0':
            return "transfer"
        elif len(input_data) > 10:
            return "contract_interaction"
        return "unknown"

    def _generate_summary(self, tx, tx_type):
        val = int(tx.get('value', '0x0'), 16) / 10**18
        if tx_type == "transfer":
            return f"A simple transfer of {val} ETH from {tx.get('from')} to {tx.get('to')}."
        elif tx_type == "contract_interaction":
            return f"A contract interaction initiated by {tx.get('from')} with contract {tx.get('to')}, carrying {val} ETH."
        return "An unknown transaction type."
