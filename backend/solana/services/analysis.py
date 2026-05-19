import logging
from .solana_service import SolanaService
from ..models import SolanaWalletAnalysis, SolanaTransactionAnalysis
from ai.services.gemma_service import GemmaService

logger = logging.getLogger('solana')


class SolanaAnalyzerService:
    def __init__(self):
        self.solana = SolanaService()
        self.ai = GemmaService()

    def analyze_wallet(self, address):
        data = self.solana.get_wallet_info(address)

        if 'error' in data and not data.get('signatures'):
            logger.error("Solana wallet fetch failed for %s: %s", address, data['error'])
            return {"success": False, "error": data['error']}

        signatures = data.get('signatures', [])
        balance_sol = data.get('balance', 0) / 10**9

        metrics = {
            "balance": balance_sol,
            "tx_count": len(signatures),
            "recent_activity": True if signatures else False
        }

        signals = []
        if len(signatures) < 2:
            signals.append("NEW_OR_INACTIVE_WALLET")
        if balance_sol > 100:
            signals.append("WHALE_WALLET")

        risk_score = self._calculate_risk_score(signals, metrics)

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

        logger.info("Solana wallet analysis saved: id=%d addr=%s score=%d signals=%s",
                     analysis.id, address, risk_score, signals)

        return {
            "success": True,
            "data": {
                "id": analysis.id,
                "risk_score": risk_score,
                "signals": signals,
                "metrics": metrics,
                "ai_summary": ai_explanation
            }
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
        else:
            summary += "Status: Failed. "

        ai_summary = self.ai.translate_transaction({
            "chain": "solana",
            "signature": signature,
            "raw_meta": meta,
            "summary_basic": summary
        })

        analysis = SolanaTransactionAnalysis.objects.create(
            signature=signature,
            interpretation=ai_summary,
            raw_data=tx_details
        )

        logger.info("Solana TX analysis saved: id=%d sig=%s", analysis.id, signature)

        return {
            "success": True,
            "data": {
                "id": analysis.id,
                "signature": signature,
                "interpretation": ai_summary
            }
        }

    def _calculate_risk_score(self, signals, metrics):
        score = 0
        if "NEW_OR_INACTIVE_WALLET" in signals: score += 15
        if metrics['tx_count'] == 0: score += 10
        return min(score, 100)
