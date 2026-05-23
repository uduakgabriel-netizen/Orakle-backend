import logging
from django.utils import timezone
from core.services.etherscan import EtherscanService
from ..models import TransactionAnalysis
from ai.services.gemma_service import GemmaService
from core.services.price_service import PriceService
from core.services.signal_explainer import SignalExplainer
from core.services.response_builder import IntelligenceResponseBuilder

logger = logging.getLogger('transactions')


class TransactionTranslatorService:
    def __init__(self):
        self.etherscan = EtherscanService()
        self.ai = GemmaService()
        self.price_service = PriceService()
        self.explainer = SignalExplainer()
        self.response_builder = IntelligenceResponseBuilder()

    def translate(self, tx_hash):
        tx_data = self.etherscan.get_transaction_receipt(tx_hash)

        if not tx_data or 'result' not in tx_data or tx_data['result'] is None:
            logger.error("Transaction not found on Etherscan: %s", tx_hash)
            return {"success": False, "error": "Transaction not found"}

        result = tx_data['result']

        tx_type = self._classify_type(result)
        summary = self._generate_summary(result, tx_type)

        # Convert ETH value to real USD value
        raw_val_hex = result.get('value', '0x0')
        if not raw_val_hex or raw_val_hex == '0x':
            raw_val_hex = '0x0'
        eth_value = int(raw_val_hex, 16) / 10**18
        usd_value = self.price_service.convert_eth_to_usd(eth_value)
        value_usd_formatted = f"${usd_value:,.2f}"

        # Generate AI Intelligence
        ai_summary = self.ai.translate_transaction({
            "tx_hash": tx_hash,
            "type": tx_type,
            "from": result.get('from'),
            "to": result.get('to'),
            "value": f"{eth_value} ETH",
            "deterministic_summary": summary
        })

        # Determine risk level based on classification
        risk_score = 20 if tx_type == "contract_interaction" else 0

        # Build standardized metrics
        gas_used = result.get('gasUsed')
        gas_price = result.get('gasPrice')
        block_number = None
        if result.get('blockNumber'):
            b_num = result.get('blockNumber')
            if str(b_num).startswith('0x'):
                block_number = int(b_num, 16)
            else:
                try:
                    block_number = int(b_num)
                except ValueError:
                    pass
        
        status_val = result.get('status', result.get('txreceipt_status'))
        if status_val is not None:
            if str(status_val).startswith('0x'):
                execution_status = int(status_val, 16)
            else:
                try:
                    execution_status = int(status_val)
                except ValueError:
                    execution_status = 1
        else:
            execution_status = 1

        input_data = result.get('input', '0x')
        selector = input_data[:10] if input_data else '0x'
        METHOD_SELECTORS = {
            "0xa9059cbb": "transfer(address,uint256)",
            "0x095ea7b3": "approve(address,uint256)",
            "0x23b872dd": "transferFrom(address,address,uint256)",
            "0x70a08231": "balanceOf(address)",
        }
        method_name = METHOD_SELECTORS.get(selector, f"unknown_method({selector})") if len(selector) == 10 else "transfer"

        metrics = {
            "gas_used": gas_used,
            "gas_price": gas_price,
            "block_number": block_number,
            "execution_status": execution_status,
            "method_name": method_name,
            "from_address": result.get('from'),
            "to_address": result.get('to'),
            "value": f"{eth_value} ETH",
            "value_usd": value_usd_formatted
        }

        # Create model instance
        analysis = TransactionAnalysis.objects.create(
            tx_hash=tx_hash,
            parsed_data=result,
            interpretation=str(ai_summary)
        )

        # Build visualization
        flow_data = [{
            "source": result.get('from', 'Unknown Sender'),
            "target": result.get('to', 'Contract/Receiver'),
            "value": f"{eth_value} ETH"
        }]

        visualization_data = {
            "risk_breakdown": [
                {
                    "name": "Method Execution",
                    "value": 30 if tx_type == "contract_interaction" else 10,
                    "severity": "medium" if tx_type == "contract_interaction" else "low"
                }
            ],
            "activity_chart": [],
            "timeline": [
                {
                    "time": "Mined",
                    "event": "Transaction Confirmed",
                    "description": f"Mined in block {block_number} with status {execution_status}."
                }
            ],
            "flow_data": flow_data
        }

        # Build standardized universal response
        response_payload = self.response_builder.build(
            type="transaction",
            chain="ethereum",
            risk_score=risk_score,
            signals=[],
            metrics=metrics,
            ai_summary=ai_summary,
            address=tx_hash,
            visualization_data=visualization_data,
            id=analysis.id
        )

        analysis.response_payload = response_payload
        analysis.save()

        logger.info("Transaction analysis saved: id=%d hash=%s type=%s", analysis.id, tx_hash, tx_type)

        return {
            "success": True,
            "data": response_payload
        }

    def _classify_type(self, tx):
        input_data = tx.get('input', '0x')
        if input_data == '0x' or input_data == '0x0':
            return "transfer"
        elif len(input_data) > 10:
            return "contract_interaction"
        return "unknown"

    def _generate_summary(self, tx, tx_type):
        raw_val_hex = tx.get('value', '0x0')
        if not raw_val_hex or raw_val_hex == '0x':
            raw_val_hex = '0x0'
        val = int(raw_val_hex, 16) / 10**18
        if tx_type == "transfer":
            return f"A simple transfer of {val} ETH from {tx.get('from')} to {tx.get('to')}."
        elif tx_type == "contract_interaction":
            return f"A contract interaction initiated by {tx.get('from')} with contract {tx.get('to')}, carrying {val} ETH."
        return "An unknown transaction type."
