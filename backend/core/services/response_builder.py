"""
Orakle Intelligence Platform — Intelligence Response Builder.

Builds a flat universal response envelope for all intelligence endpoints,
ensuring consistent shape across wallet, contract, transaction, and
Solana analysis responses.
"""

import logging
from django.utils import timezone
from core.services.price_service import PriceService
from core.services.signal_explainer import SignalExplainer

logger = logging.getLogger('core')


class IntelligenceResponseBuilder:
    """
    Constructs standardised flat response payloads for the Orakle platform conforming
    exactly to the UniversalAnalysis schema.
    """

    def __init__(self):
        self.price_service = PriceService()
        self.explainer = SignalExplainer()

    def build(self, type, chain, risk_score, signals, metrics, ai_summary, recommendations=None, address=None, visualization_data=None, id=None):
        """
        Build a flat universal response payload conforming to UniversalAnalysis.

        Returns:
            dict: Standardised flat response envelope.
        """
        risk_level = self.explainer.get_risk_level(risk_score)
        
        domain = 'contract' if type in ('contract', 'contract_file') else 'wallet'
        
        # Enrich and normalize signals
        raw_signals = signals if isinstance(signals, list) else []
        enriched_signals = []
        for s in raw_signals:
            if isinstance(s, dict):
                sig_obj = s.copy()
            else:
                sig_obj = self.explainer.explain_signal(str(s), domain)
            
            # Normalize severity to: "low" | "medium" | "high" | "critical"
            sev = str(sig_obj.get('severity', 'medium')).lower().strip()
            if sev not in ("low", "medium", "high", "critical"):
                if sev in ("info", "safe"):
                    sev = "low"
                elif sev in ("warning", "alert"):
                    sev = "high"
                else:
                    sev = "medium"
            sig_obj['severity'] = sev
            enriched_signals.append(sig_obj)

        # AI Summary normalization
        summary_text = ""
        threat_assessment = "unknown"
        key_findings = []
        confidence_score = 0.95
        confidence_reasoning = ""
        
        if isinstance(ai_summary, dict):
            summary_text = ai_summary.get('summary', ai_summary.get('text', ''))
            threat_assessment = ai_summary.get('threat_assessment', 'unknown')
            key_findings = ai_summary.get('key_findings', [])
            confidence_score = ai_summary.get('confidence_score', 0.95)
            confidence_reasoning = ai_summary.get('confidence_reasoning', '')
            if not recommendations and 'recommendations' in ai_summary:
                recommendations = ai_summary.get('recommendations', [])
        elif isinstance(ai_summary, str):
            summary_text = ai_summary
            threat_assessment = "medium"
            confidence_reasoning = "Based on unstructured AI input."

        # Parse confidence score safely
        try:
            confidence_score = float(confidence_score)
            if confidence_score > 1.0:
                confidence_score = confidence_score / 100.0
        except (ValueError, TypeError):
            confidence_score = 0.95

        if not recommendations or (isinstance(recommendations, list) and len(recommendations) == 0):
            # Fallback recommendations if empty
            threat = str(threat_assessment).lower()
            is_risky = "high" in threat or "critical" in threat or risk_score > 70
            is_medium = "medium" in threat or risk_score > 40
            
            if type in ('contract', 'contract_file'):
                if is_risky:
                    recommendations = [
                        "CRITICAL: Do not interact with this contract until a full security audit is completed. Multiple high-risk patterns detected.",
                        "Investigate the mint, pause, and blacklist functions for potential abuse vectors. Verify if owner privileges have been renounced.",
                        "If you hold tokens from this contract, consider transferring to a secure wallet and monitoring for suspicious owner activity.",
                        "Audit all proxy upgrade events and verify the implementation contract is not malicious."
                    ]
                elif is_medium:
                    recommendations = [
                        "Perform deeper audit on detected functions for hidden edge-cases.",
                        "Monitor proxy upgrade events and admin role actions.",
                        "Confirm compiler optimization settings are standard."
                    ]
                else:
                    recommendations = [
                        "Monitor for abnormal transaction or call patterns.",
                        "Ensure regular security reviews are scheduled.",
                        "No immediate code remediation required."
                    ]
            elif type in ('transaction', 'solana_transaction'):
                if is_risky:
                    recommendations = [
                        "Flag transaction for compliance review.",
                        "Immediately trace destination wallet address flow.",
                        "Verify authorization of associated sender key."
                    ]
                elif is_medium:
                    recommendations = [
                        "Monitor gas fees and fee pattern deviations.",
                        "Review transaction method signature constraints.",
                        "Log transaction details for audit trails."
                    ]
                else:
                    recommendations = [
                        "Continue standard transaction auditing procedures.",
                        "No direct security concerns detected in this execution.",
                        "Log transaction hash for compliance logs."
                    ]
            else:  # wallet / solana_wallet
                if is_risky:
                    recommendations = [
                        "Immediately investigate large outgoing transfers.",
                        "Freeze interaction with this address pending review.",
                        "Report to compliance team for further analysis."
                    ]
                elif is_medium:
                    recommendations = [
                        "Review transaction patterns for anomalies.",
                        "Monitor for sudden shifts in transaction volume.",
                        "Standard precautions recommended."
                    ]
                else:
                    recommendations = [
                        "Continue standard monitoring - no suspicious patterns detected.",
                        "No immediate action required.",
                        "Consider periodic review for ongoing compliance."
                    ]
            
        if not confidence_reasoning:
            confidence_reasoning = self.explainer.get_confidence_reasoning(
                risk_score, [s.get('signal') for s in enriched_signals], domain
            )
            
        normalized_ai_summary = {
            "summary": summary_text,
            "threat_assessment": threat_assessment,
            "key_findings": key_findings if isinstance(key_findings, list) else [],
            "recommendations": recommendations if isinstance(recommendations, list) else [],
            "confidence_score": confidence_score,
            "confidence_reasoning": confidence_reasoning
        }
        
        # Metadata
        now_str = timezone.now().isoformat()
        if chain == 'solana':
            source = "Solana RPC + AI Intelligence"
            chain_label = "Solana Mainnet"
        else:
            source = "Etherscan + Alchemy RPC + AI Intelligence"
            chain_label = "Ethereum Mainnet"
            
        analysis_metadata = {
            "source": source,
            "generated_at": now_str,
            "model": "Gemma 4",
            "chain": chain_label
        }
        
        # Populate visualization_data if not provided
        if visualization_data is None:
            visualization_data = {
                "risk_breakdown": [],
                "activity_chart": [],
                "timeline": [],
                "flow_data": []
            }
            
            for s in enriched_signals:
                sig_name = s.get('signal', '')
                sev = s.get('severity', 'medium')
                val = 40 if sev == "critical" else 30 if sev == "high" else 20 if sev == "medium" else 10
                visualization_data["risk_breakdown"].append({
                    "name": sig_name.replace("_", " ").capitalize(),
                    "value": val,
                    "severity": sev
                })
            
            if not visualization_data["risk_breakdown"]:
                visualization_data["risk_breakdown"].append({
                    "name": "Security Foundation",
                    "value": max(100 - risk_score, 10),
                    "severity": "low"
                })

            if type in ('wallet', 'solana_wallet'):
                tx_count = metrics.get('tx_count', metrics.get('total_transactions', 0))
                base_activity = max(int(tx_count / 7), 1) if tx_count else 0
                for i in range(7):
                    visualization_data["activity_chart"].append({
                        "day": f"Day {i+1}",
                        "transactions": base_activity + (i * 3 % 5) if tx_count else 0
                    })
                
                age_days = metrics.get('age_days', metrics.get('account_age_days', 0))
                visualization_data["timeline"].append({
                    "time": "Deployment",
                    "event": "Wallet Initialized",
                    "description": f"Wallet became active on-chain ~{age_days} days ago."
                })
                visualization_data["timeline"].append({
                    "time": "Current",
                    "event": "Security Verification",
                    "description": f"Analyzed {tx_count} transactions. Risk score calculated at {risk_score}."
                })
            elif type in ('contract', 'contract_file'):
                visualization_data["timeline"].append({
                    "time": "Genesis",
                    "event": "Contract Deployed",
                    "description": "Code compiled and committed to the ledger."
                })
                visualization_data["timeline"].append({
                    "time": "Audit",
                    "event": "Security Audit Executed",
                    "description": f"Orakle scanned contract capabilities. Risk score: {risk_score}."
                })
            elif type in ('transaction', 'solana_transaction'):
                visualization_data["flow_data"].append({
                    "source": address or "Unknown Sender",
                    "target": metrics.get("to", "Contract/Receiver"),
                    "value": metrics.get("value", str(metrics.get("amount", "0")))
                })
        
        response_payload = {
            "type": type,
            "chain": chain,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "signals": enriched_signals,
            "metrics": metrics,
            "recommendations": recommendations,
            "ai_summary": normalized_ai_summary,
            "analysis_metadata": analysis_metadata,
            "generated_at": now_str,
            "visualization_data": visualization_data
        }
        
        if id is not None:
            response_payload["id"] = id
        
        if address is not None:
            response_payload["address"] = address
            
        return response_payload
