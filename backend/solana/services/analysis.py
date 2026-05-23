import logging
from .solana_service import SolanaService
from ..models import SolanaWalletAnalysis, SolanaTransactionAnalysis
from ai.services.gemma_service import GemmaService
from core.services.response_builder import IntelligenceResponseBuilder

logger = logging.getLogger('solana')


class SolanaAnalyzerService:
    def __init__(self):
        self.solana = SolanaService()
        self.ai = GemmaService()
        self.response_builder = IntelligenceResponseBuilder()

    def analyze_wallet(self, address):
        data = self.solana.get_wallet_info(address)

        if 'error' in data and not data.get('signatures'):
            logger.error("Solana wallet fetch failed for %s: %s", address, data['error'])
            return {"success": False, "error": data['error']}

        signatures = data.get('signatures', [])
        balance_sol = data.get('balance', 0) / 10**9
        tx_count = len(signatures)
        is_whale = balance_sol > 100

        # Classify activity frequency
        if tx_count > 50:
            activity_frequency = "high"
        elif tx_count > 10:
            activity_frequency = "medium"
        else:
            activity_frequency = "low"

        # Estimate account age
        account_age_days = max(tx_count * 2, 5) if signatures else 1

        metrics = {
            "balance": balance_sol,
            "total_transactions": tx_count,
            "activity_frequency": activity_frequency,
            "is_whale": is_whale,
            "account_age_days": account_age_days,
            "last_active_days": 1
        }

        signals = []
        if tx_count < 2:
            signals.append("NEW_OR_INACTIVE_WALLET")
        if is_whale:
            signals.append("WHALE_WALLET")

        risk_score = self._calculate_risk_score(signals, metrics)

        # Generate AI Intelligence
        ai_explanation = self.ai.explain_wallet({
            "chain": "solana",
            "address": address,
            "metrics": metrics,
            "signals": signals,
            "risk_score": risk_score
        })

        analysis = SolanaWalletAnalysis.objects.create(
            wallet_address=address,
            risk_score=risk_score,
            signals=signals,
            metrics=metrics
        )

        # Build standardized universal response
        response_payload = self.response_builder.build(
            type="solana_wallet",
            chain="solana",
            risk_score=risk_score,
            signals=signals,
            metrics=metrics,
            ai_summary=ai_explanation,
            address=address,
            id=analysis.id
        )

        analysis.response_payload = response_payload
        analysis.save()

        logger.info("Solana wallet analysis saved: id=%d addr=%s score=%d signals=%s",
                     analysis.id, address, risk_score, signals)

        return {
            "success": True,
            "data": response_payload
        }

    def translate_transaction(self, signature):
        tx_details = self.solana.get_transaction_details(signature)

        if not tx_details:
            logger.error("Solana transaction not found: %s", signature)
            return {"success": False, "error": "Transaction not found or could not be retrieved."}

        summary = "Solana transaction detected. "
        meta = tx_details.get('meta', {})
        if meta and meta.get('err') is None:
            summary += "Status: Success. "
            status = 1
        else:
            summary += "Status: Failed. "
            status = 0

        # Extract fee and basic metrics
        fee = meta.get('fee', 0) / 10**9 if meta else 0
        account_keys = tx_details.get('transaction', {}).get('message', {}).get('accountKeys', [])
        sender = account_keys[0] if account_keys else "Unknown Sender"
        receiver = account_keys[1] if len(account_keys) > 1 else "Unknown Receiver"

        ai_summary = self.ai.translate_transaction({
            "chain": "solana",
            "signature": signature,
            "raw_meta": meta,
            "summary_basic": summary
        })

        analysis = SolanaTransactionAnalysis.objects.create(
            signature=signature,
            interpretation=str(ai_summary),
            raw_data=tx_details
        )

        # Build visualization
        flow_data = [{
            "source": sender,
            "target": receiver,
            "value": f"{fee} SOL (fee)"
        }]

        visualization_data = {
            "risk_breakdown": [
                {
                    "name": "Solana Transaction",
                    "value": 10,
                    "severity": "low"
                }
            ],
            "activity_chart": [],
            "timeline": [
                {
                    "time": "Mined",
                    "event": "Transaction Settled",
                    "description": f"Settled at slot {tx_details.get('slot', 0)} with status {status}."
                }
            ],
            "flow_data": flow_data
        }

        # Build standardized universal response
        response_payload = self.response_builder.build(
            type="solana_transaction",
            chain="solana",
            risk_score=10 if status == 0 else 0, # Minor risk if transaction failed
            signals=[],
            metrics={
                "gas_used": fee,
                "gas_price": 0,
                "block_number": tx_details.get('slot', 0),
                "execution_status": status,
                "method_name": "transfer" if len(account_keys) == 2 else "program_execution",
                "sender": sender,
                "receiver": receiver,
                "fee": fee
            },
            ai_summary=ai_summary,
            address=signature,
            visualization_data=visualization_data,
            id=analysis.id
        )

        analysis.response_payload = response_payload
        analysis.save()

        logger.info("Solana TX analysis saved: id=%d sig=%s", analysis.id, signature)

        return {
            "success": True,
            "data": response_payload
        }

    def _calculate_risk_score(self, signals, metrics):
        score = 0
        if "NEW_OR_INACTIVE_WALLET" in signals: score += 15
        if metrics['total_transactions'] == 0: score += 10
        return min(score, 100)
