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
        "MINT FUNCTION: The contract has an unrestricted mint function that allows the owner to create unlimited new tokens. This could lead to hyperinflation and total loss of token value for all holders.",
        "Recommendation: Implement access controls, add a max supply cap, or use a timelock on the mint function."
    ),
    ("Trading can be paused by owner", "contract"): (
        "high",
        "PAUSE CONTROL: The owner can pause all trading activity on this contract at any time. During a pause, holders cannot sell or transfer tokens, which enables potential rug-pull scenarios.",
        "Recommendation: Add a timelock delay before pausing takes effect, or transition to community governance for pause decisions."
    ),
    ("Contract contains blacklist capabilities", "contract"): (
        "high",
        "BLACKLIST FUNCTION: The owner can blacklist any address, permanently preventing them from interacting with the contract. This centralized control could be used to freeze user funds without recourse.",
        "Recommendation: Consider renouncing blacklist authority, implementing a transparent appeals process, or delegating to a multi-sig."
    ),
    ("Owner can adjust transaction taxes", "contract"): (
        "high",
        "TAX MANIPULATION: The owner can modify buy/sell tax rates after deployment with no upper bound. Taxes could be raised to 99-100%, effectively locking seller funds and preventing any meaningful trades.",
        "Recommendation: Implement a hard-coded maximum tax cap (e.g., 10%) and add a timelock for tax changes."
    ),
    ("Liquidity or funds withdrawal risk detected", "contract"): (
        "critical",
        "LIQUIDITY DRAIN RISK: A function was detected that allows the owner to withdraw pooled liquidity or user funds directly. This is a direct rug-pull vector — all pooled funds can be drained instantly by the contract owner.",
        "Recommendation: Remove owner withdrawal of LP tokens, implement a vesting schedule, or lock liquidity in a third-party locker."
    ),
    ("Owner privileges can be transferred or renounced", "contract"): (
        "medium",
        "OWNERSHIP CONTROL: The contract has transferOwnership and/or renounceOwnership functions. If ownership is transferred, a new unknown party gains all admin privileges. If renounced, the contract becomes permanently immutable.",
        "Recommendation: Verify ownership status. If not renounced, transition owner privileges to a multi-signature wallet or DAO."
    ),
    ("Contract supports upgrades (logic can be replaced)", "contract"): (
        "high",
        "UPGRADEABLE CONTRACT: The contract contains upgrade mechanisms that allow the entire logic to be replaced post-deployment. A malicious upgrade could introduce hidden backdoors, drain functions, or break all existing functionality.",
        "Recommendation: Ensure the implementation contract is immutable, add a timelock to upgrades, and use a multi-sig for admin actions."
    ),
    ("Contract is an upgradeable proxy (logic can be changed by owner)", "contract"): (
        "high",
        "PROXY PATTERN: This is a proxy contract — the implementation logic can be completely swapped by the owner at any time. All contract behavior can change post-deployment without holder consent or notification.",
        "Recommendation: Verify the proxy admin is a multi-sig or DAO. Check if a timelock exists before upgrades take effect."
    ),
    ("Minter roles can be configured by admin", "contract"): (
        "medium",
        "MINTER CONFIGURATION: The admin can assign minting privileges to arbitrary addresses. If the admin key is compromised or malicious, unauthorized addresses could mint tokens freely.",
        "Recommendation: Restrict minter role configuration to a multi-sig wallet and audit all current minter addresses."
    ),
    ("Contract contains SELFDESTRUCT (funds can be stolen/contract destroyed)", "contract"): (
        "critical",
        "SELFDESTRUCT OPCODE: The contract contains the SELFDESTRUCT opcode, which can permanently destroy the contract and send all remaining ETH to a specified address. This is an extreme risk — the entire contract and all funds can be wiped instantly.",
        "Recommendation: Avoid interacting with contracts containing SELFDESTRUCT. If you own this contract, remove the opcode and redeploy."
    ),
    ("Contract uses DELEGATECALL (risk of logic hijacking)", "contract"): (
        "high",
        "DELEGATECALL USAGE: The contract uses delegatecall, which allows external code to execute in this contract's context with full access to its storage and funds. If the delegate target is compromised, all assets are at risk.",
        "Recommendation: Ensure the implementation is immutable or has strict access controls. Verify the delegate target address is trusted."
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
