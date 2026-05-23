"""
Orakle Intelligence Platform — Signal Explainer Service.

Enriches raw deterministic signals into structured explanations with
severity, impact, and human-readable descriptions. Also provides
risk-level classification and confidence reasoning generation.
"""

import logging

logger = logging.getLogger('core')


# Signal definitions keyed by (signal_name, domain).
# Each entry: (severity, explanation, impact)
SIGNAL_DEFINITIONS = {
    # Wallet signals
    ("NEW_WALLET", "wallet"): (
        "medium",
        "This wallet was created very recently (less than 7 days ago).",
        "New wallets have no established history, making behavioral assessment less reliable."
    ),
    ("HIGH_FREQUENCY_NEW_WALLET", "wallet"): (
        "high",
        "This brand-new wallet has executed an unusually high volume of transactions in a very short time.",
        "May indicate automated bot activity, wash trading, or a sybil attack pattern."
    ),
    ("NEW_OR_INACTIVE_WALLET", "wallet"): (
        "medium",
        "This wallet is either newly created or has been inactive for a long period.",
        "Low historical data reduces confidence in behavioral risk assessment."
    ),
    ("WHALE_WALLET", "wallet"): (
        "low",
        "This wallet holds a very large balance (>100 SOL or equivalent).",
        "Large holders can influence market prices; monitor for unusual outflows."
    ),
    # Contract signals
    ("Owner can mint unlimited supply", "contract"): (
        "critical",
        "The contract owner has an unrestricted mint function.",
        "Token supply can be inflated at will, diluting holder value to zero."
    ),
    ("Trading can be paused by owner", "contract"): (
        "high",
        "The owner can pause all trading on this contract.",
        "Holders may be unable to sell during a pause, enabling rug-pull scenarios."
    ),
    ("Contract contains blacklist capabilities", "contract"): (
        "high",
        "The contract has a blacklist mechanism that can block specific addresses.",
        "Targeted addresses can be permanently frozen from transacting."
    ),
    ("Owner can adjust transaction taxes", "contract"): (
        "high",
        "The owner can modify buy/sell tax rates after deployment.",
        "Taxes could be raised to 100%, effectively locking seller funds."
    ),
    ("Liquidity or funds withdrawal risk detected", "contract"): (
        "critical",
        "A function allowing the owner to withdraw pooled liquidity or user funds was detected.",
        "Direct rug-pull vector — all pooled funds can be drained by the owner."
    ),
    ("Owner privileges can be transferred or renounced", "contract"): (
        "medium",
        "Ownership transfer or renounce functions are present.",
        "If renounced, the contract becomes immutable; if transferred, a new owner gains all privileges."
    ),
    ("Contract supports upgrades (logic can be replaced)", "contract"): (
        "high",
        "The contract contains upgrade mechanisms allowing logic replacement.",
        "A malicious upgrade could introduce hidden backdoors or drain functions."
    ),
    ("Contract is an upgradeable proxy (logic can be changed by owner)", "contract"): (
        "high",
        "This is a proxy contract — the implementation logic can be swapped by the owner.",
        "All contract behavior can be changed post-deployment without holder consent."
    ),
    ("Minter roles can be configured by admin", "contract"): (
        "medium",
        "Admin can assign minting privileges to arbitrary addresses.",
        "Risk of unauthorized minting if admin key is compromised."
    ),
    ("Contract contains SELFDESTRUCT (funds can be stolen/contract destroyed)", "contract"): (
        "critical",
        "The SELFDESTRUCT opcode is present in the contract source.",
        "The entire contract can be destroyed and remaining funds sent to the caller."
    ),
    ("Contract uses DELEGATECALL (risk of logic hijacking)", "contract"): (
        "high",
        "DELEGATECALL is used, allowing external code to execute in this contract's context.",
        "If the delegate target is compromised, the contract's storage and funds are at risk."
    ),
}


class SignalExplainer:
    """
    Enriches raw signal strings into structured, human-readable explanations
    and provides risk-level classification.
    """

    RISK_LEVELS = [
        (0, "safe"),
        (20, "low"),
        (40, "medium"),
        (60, "high"),
        (80, "critical"),
    ]

    def explain_signal(self, signal, domain='wallet'):
        """
        Enrich a single signal string.

        Args:
            signal: Raw signal string (e.g. 'NEW_WALLET').
            domain: Context domain — 'wallet' or 'contract'.

        Returns:
            dict: {signal, severity, explanation, impact}
        """
        key = (signal, domain)
        if key in SIGNAL_DEFINITIONS:
            severity, explanation, impact = SIGNAL_DEFINITIONS[key]
        else:
            # Fallback for unknown signals
            severity = "info"
            explanation = signal.replace("_", " ").capitalize()
            impact = "No detailed impact analysis available for this signal."
            logger.debug("SignalExplainer: unknown signal '%s' in domain '%s'", signal, domain)

        return {
            "signal": signal,
            "severity": severity,
            "explanation": explanation,
            "impact": impact,
        }

    def explain_signals(self, signals, domain='wallet'):
        """
        Enrich a list of raw signal strings.

        Args:
            signals: List of raw signal strings.
            domain: Context domain — 'wallet' or 'contract'.

        Returns:
            list[dict]: List of enriched signal dicts.
        """
        if not signals:
            return []
        return [self.explain_signal(s, domain) for s in signals]

    def get_risk_level(self, risk_score):
        """
        Classify a numeric risk score (0-100) into a human-readable level.

        Args:
            risk_score: Integer risk score, 0–100.

        Returns:
            str: One of 'safe', 'low', 'medium', 'high', 'critical'.
        """
        try:
            risk_score = int(risk_score)
        except (ValueError, TypeError):
            return "unknown"

        level = "safe"
        for threshold, label in self.RISK_LEVELS:
            if risk_score >= threshold:
                level = label
        return level

    def get_confidence_reasoning(self, risk_score, signals, domain='wallet'):
        """
        Generate a human-readable confidence reasoning string.

        Args:
            risk_score: Integer risk score.
            signals: List of raw signal strings.
            domain: 'wallet' or 'contract'.

        Returns:
            str: A reasoning paragraph about analysis confidence.
        """
        signal_count = len(signals) if signals else 0
        risk_level = self.get_risk_level(risk_score)

        if signal_count == 0:
            return (
                f"No deterministic signals detected. The {domain} shows no suspicious "
                f"patterns based on available on-chain data. Confidence is moderate due "
                f"to limited signal coverage."
            )

        severity_counts = {}
        for s in signals:
            enriched = self.explain_signal(s, domain)
            sev = enriched['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        parts = [
            f"Analysis detected {signal_count} signal(s) across the {domain}.",
            f"Overall risk level: {risk_level} (score: {risk_score}/100).",
        ]

        if severity_counts.get('critical', 0) > 0:
            parts.append(
                f"{severity_counts['critical']} critical-severity signal(s) significantly "
                f"increase confidence that this {domain} poses genuine risk."
            )
        if severity_counts.get('high', 0) > 0:
            parts.append(
                f"{severity_counts['high']} high-severity signal(s) detected."
            )

        parts.append(
            "Confidence is based on deterministic on-chain data verified by "
            "Etherscan, Alchemy RPC, and the Orakle analysis engine."
        )

        return " ".join(parts)
