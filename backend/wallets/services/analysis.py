import logging
import time
from core.services.etherscan import EtherscanService
from ..models import WalletAnalysis
from ai.services.gemma_service import GemmaService
from core.services.price_service import PriceService
from core.services.signal_explainer import SignalExplainer
from core.services.response_builder import IntelligenceResponseBuilder

logger = logging.getLogger('wallets')


class WalletAnalyzerService:
    def __init__(self):
        self.etherscan = EtherscanService()
        self.ai = GemmaService()
        self.price_service = PriceService()
        self.explainer = SignalExplainer()
        self.response_builder = IntelligenceResponseBuilder()

    def analyze(self, address):
        start_time = time.time()
        logger.info("Starting analysis for wallet: %s", address)
        
        tx_data = self.etherscan.get_wallet_transactions(address)
        logger.info("Etherscan fetch took %.2fs", time.time() - start_time)

        if tx_data.get('status') != '1':
            error_msg = tx_data.get('result', tx_data.get('message', 'Failed to fetch data'))
            logger.error("Etherscan fetch failed for wallet %s: %s", address, error_msg)
            return {"success": False, "error": error_msg}

        transactions = tx_data.get('result', [])
        
        metrics_start = time.time()
        metrics = self._calculate_metrics(transactions)
        signals = self._detect_signals(transactions, metrics)
        risk_score = self._calculate_risk_score(signals, metrics)
        logger.info("Metrics and signals calculation took %.2fs", time.time() - metrics_start)

        # Generate AI Intelligence
        ai_start = time.time()
        ai_summary = self.ai.explain_wallet({
            "address": address,
            "risk_score": risk_score,
            "signals": signals,
            "metrics": metrics
        })
        logger.info("AI reasoning took %.2fs", time.time() - ai_start)

        db_start = time.time()
        analysis = WalletAnalysis.objects.create(
            wallet_address=address,
            risk_score=risk_score,
            signals=signals,
            raw_metrics=metrics
        )
        logger.info("Database creation took %.2fs", time.time() - db_start)

        # Build standardized universal response data
        response_data = self.response_builder.build(
            type="wallet",
            chain="ethereum",
            risk_score=risk_score,
            signals=signals,
            metrics=metrics,
            ai_summary=ai_summary,
            address=address,
            id=analysis.id
        )

        analysis.response_payload = response_data
        analysis.save()
        logger.info("Total analysis time: %.2fs", time.time() - start_time)

        logger.info("Wallet analysis saved: id=%d addr=%s score=%d signals=%s",
                     analysis.id, address, risk_score, signals)

        return {
            "success": True,
            "data": response_data
        }

    def _calculate_metrics(self, txs):
        if not txs:
            return {
                "tx_count": 0,
                "total_transactions": 0,
                "age_days": 0,
                "account_age_days": 0,
                "last_active_days": 0,
                "activity_level": "Low",
                "total_eth_volume": 0.0,
                "total_usd_volume": "$0.00"
            }

        latest_tx = int(txs[0]['timeStamp'])
        earliest_tx = int(txs[-1]['timeStamp'])
        age_seconds = int(time.time()) - earliest_tx

        # Calculate total ETH volume from transactions
        total_wei_volume = 0
        for tx in txs:
            try:
                total_wei_volume += int(tx.get('value', '0'))
            except (ValueError, TypeError):
                pass
        total_eth_volume = total_wei_volume / 10**18
        usd_value = self.price_service.convert_eth_to_usd(total_eth_volume)
        total_usd_volume = f"${usd_value:,.2f}"

        tx_count = len(txs)
        activity_level = "High" if tx_count > 50 else "Medium" if tx_count > 10 else "Low"

        return {
            "tx_count": tx_count,
            "total_transactions": tx_count,
            "age_days": age_seconds // 86400,
            "account_age_days": age_seconds // 86400,
            "last_active_days": (int(time.time()) - latest_tx) // 86400,
            "activity_level": activity_level,
            "total_eth_volume": round(total_eth_volume, 4),
            "total_usd_volume": total_usd_volume
        }

    def _detect_signals(self, txs, metrics):
        signals = []
        age_days = metrics.get('age_days', 0)
        tx_count = metrics.get('tx_count', 0)

        if age_days < 7:
            signals.append("NEW_WALLET")
        elif age_days < 30:
            signals.append("RELATIVELY_NEW_WALLET")

        # High frequency activity detection
        if tx_count > 50 and age_days < 2:
            signals.append("HIGH_FREQUENCY_NEW_WALLET")
        elif tx_count > 200 and age_days < 14:
            signals.append("SUSPICIOUS_HIGH_ACTIVITY")

        return signals

    def _calculate_risk_score(self, signals, metrics):
        score = 0
        if "NEW_WALLET" in signals: score += 20
        if "RELATIVELY_NEW_WALLET" in signals: score += 10
        if "HIGH_FREQUENCY_NEW_WALLET" in signals: score += 40
        if "SUSPICIOUS_HIGH_ACTIVITY" in signals: score += 30

        if metrics.get('tx_count') == 0: score += 10

        return min(score, 100)
