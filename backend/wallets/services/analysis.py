import logging
import time
from core.services.etherscan import EtherscanService
from ..models import WalletAnalysis

logger = logging.getLogger('wallets')


class WalletAnalyzerService:
    def __init__(self):
        self.etherscan = EtherscanService()

    def analyze(self, address):
        tx_data = self.etherscan.get_wallet_transactions(address)

        if tx_data.get('status') != '1':
            error_msg = tx_data.get('result', tx_data.get('message', 'Failed to fetch data'))
            logger.error("Etherscan fetch failed for wallet %s: %s", address, error_msg)
            return {"success": False, "error": error_msg}

        transactions = tx_data.get('result', [])

        metrics = self._calculate_metrics(transactions)
        signals = self._detect_signals(transactions, metrics)
        risk_score = self._calculate_risk_score(signals, metrics)

        analysis = WalletAnalysis.objects.create(
            wallet_address=address,
            risk_score=risk_score,
            signals=signals,
            raw_metrics=metrics
        )

        logger.info("Wallet analysis saved: id=%d addr=%s score=%d signals=%s",
                     analysis.id, address, risk_score, signals)

        return {
            "success": True,
            "data": {
                "id": analysis.id,
                "risk_score": risk_score,
                "signals": signals,
                "metrics": metrics
            }
        }

    def _calculate_metrics(self, txs):
        if not txs:
            return {"tx_count": 0, "age_days": 0}

        latest_tx = int(txs[0]['timeStamp'])
        earliest_tx = int(txs[-1]['timeStamp'])
        age_seconds = int(time.time()) - earliest_tx

        return {
            "tx_count": len(txs),
            "age_days": age_seconds // 86400,
            "last_active_days": (int(time.time()) - latest_tx) // 86400
        }

    def _detect_signals(self, txs, metrics):
        signals = []

        if metrics['age_days'] < 7:
            signals.append("NEW_WALLET")

        if metrics['tx_count'] > 50 and metrics['age_days'] < 2:
            signals.append("HIGH_FREQUENCY_NEW_WALLET")

        return signals

    def _calculate_risk_score(self, signals, metrics):
        score = 0
        if "NEW_WALLET" in signals: score += 20
        if "HIGH_FREQUENCY_NEW_WALLET" in signals: score += 40

        if metrics['tx_count'] == 0: score += 10

        return min(score, 100)
