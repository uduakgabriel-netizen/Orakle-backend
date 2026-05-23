import re
import json
import logging
from core.services.etherscan import EtherscanService
from ..models import ContractAnalysis
from ai.services.gemma_service import GemmaService
from core.services.response_builder import IntelligenceResponseBuilder

logger = logging.getLogger('contracts')

# Known proxy storage slots (EIP-1967)
PROXY_PATTERNS = {
    'EIP-1967': r'0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc',
    'OpenZeppelin': r'\bdelegatecall\b',
    'UUPS': r'upgradeTo\(address\)',
    'Transparent': r'TransparentUpgradeableProxy',
}


class ContractAnalyzerService:
    def __init__(self):
        self.etherscan = EtherscanService()
        self.ai = GemmaService()
        self.response_builder = IntelligenceResponseBuilder()

    def analyze(self, address):
        source_data = self.etherscan.get_contract_source_code(address)

        if source_data.get('status') != '1' or not source_data.get('result'):
            logger.error("Etherscan returned no data for contract %s", address)
            return {"success": False, "error": "Could not fetch contract data from Etherscan."}

        result = source_data['result'][0]
        abi_string = result.get('ABI', '')
        source_code = result.get('SourceCode', '')
        implementation_address = result.get('Implementation', '')

        if not abi_string or abi_string == 'Contract source code not verified':
            return {"success": False, "error": "Contract source not verified and ABI is unavailable."}

        # Detect proxy contract
        is_proxy = bool(implementation_address) or self._detect_proxy_pattern(source_code)
        proxy_metadata = {}

        if is_proxy:
            proxy_metadata['is_proxy'] = True
            proxy_metadata['proxy_type'] = self._classify_proxy_type(source_code)
            logger.info("Proxy contract detected at %s (type: %s)", address, proxy_metadata['proxy_type'])

            if implementation_address:
                proxy_metadata['implementation_address'] = implementation_address
                impl_abi = self.etherscan.get_implementation_abi(implementation_address)
                if impl_abi:
                    logger.info("Fetched implementation ABI for %s -> %s", address, implementation_address)
                    abi_string = impl_abi

        metadata = {
            "name": result.get('ContractName'),
            "compiler": result.get('CompilerVersion'),
        }
        if proxy_metadata:
            metadata['proxy'] = proxy_metadata

        return self.run_analysis_on_source(
            address=address,
            source_code=source_code,
            abi_string=abi_string,
            metadata=metadata
        )

    def run_analysis_on_source(self, address, source_code, abi_string, metadata=None, type="contract"):
        try:
            if not abi_string:
                functions = re.findall(r"function\s+(\w+)", source_code)
            else:
                abi = json.loads(abi_string)
                functions = self._detect_functions_from_abi(abi)
        except json.JSONDecodeError:
            logger.error("Failed to parse ABI JSON for %s", address)
            return {"success": False, "error": "Failed to parse contract ABI."}

        flags = self._analyze_permissions_and_risks(functions, source_code)

        # Add proxy-specific risk flag
        is_proxy = metadata.get('proxy', {}).get('is_proxy', False) if metadata else False
        if is_proxy:
            flags.append("Contract is an upgradeable proxy (logic can be changed by owner)")

        risk_score = self._calculate_risk_score(flags)

        # Generate AI Intelligence
        ai_input = {
            "contract_address": address,
            "risk_score": risk_score,
            "signals": flags,
            "detected_functions": functions
        }
        if source_code:
            ai_input["source_code_preview"] = source_code[:1000]

        ai_summary = self.ai.explain_contract(ai_input)

        # Build metadata and metrics
        is_verified = bool(abi_string and abi_string != 'Contract source code not verified')
        contract_name = ""
        compiler_version = ""
        if metadata:
            contract_name = metadata.get("name", metadata.get("contract_name", ""))
            compiler_version = metadata.get("compiler", metadata.get("compiler_version", ""))
        
        metadata_payload = {
            "contract_name": contract_name or "Unknown",
            "compiler_version": compiler_version or "Unknown",
            "is_verified": is_verified,
            "is_proxy": is_proxy
        }

        dangerous_capabilities = []
        for flag in flags:
            if "delegatecall" in flag.lower():
                dangerous_capabilities.append("delegatecall")
            if "selfdestruct" in flag.lower():
                dangerous_capabilities.append("selfdestruct")
            if "tx.origin" in flag.lower():
                dangerous_capabilities.append("tx.origin")
            if "mint" in flag.lower():
                dangerous_capabilities.append("mint")
            if "blacklist" in flag.lower():
                dangerous_capabilities.append("blacklist")
            if "pause" in flag.lower():
                dangerous_capabilities.append("pause")
            if "upgrade" in flag.lower():
                dangerous_capabilities.append("upgrade")
            if "timestamp" in flag.lower():
                dangerous_capabilities.append("block.timestamp")

        metrics = {
            "contract_name": metadata_payload["contract_name"],
            "compiler_version": metadata_payload["compiler_version"],
            "is_verified": metadata_payload["is_verified"],
            "is_proxy": metadata_payload["is_proxy"],
            "detected_functions": functions,
            "dangerous_capabilities": dangerous_capabilities
        }

        # Create model instance
        analysis = ContractAnalysis.objects.create(
            contract_address=address,
            detected_functions=functions,
            risk_flags=flags,
            risk_score=risk_score,
            metadata=metadata_payload
        )

        # Build standardized universal response
        response_payload = self.response_builder.build(
            type=type,
            chain="ethereum",
            risk_score=risk_score,
            signals=flags,
            metrics=metrics,
            ai_summary=ai_summary,
            address=address,
            id=analysis.id
        )

        analysis.response_payload = response_payload
        analysis.save()

        logger.info("Contract analysis saved: id=%d addr=%s score=%d funcs=%d flags=%d",
                     analysis.id, address, risk_score, len(functions), len(flags))

        return {
            "success": True,
            "data": response_payload
        }

    def _detect_proxy_pattern(self, source_code):
        """Lightweight check for common proxy patterns in source code."""
        if not source_code:
            return False
        for pattern_name, pattern in PROXY_PATTERNS.items():
            if re.search(pattern, source_code):
                return True
        return False

    def _classify_proxy_type(self, source_code):
        """Classify the proxy type based on source code patterns."""
        if not source_code:
            return "unknown"
        if 'TransparentUpgradeableProxy' in source_code:
            return "transparent"
        if 'UUPSUpgradeable' in source_code or 'upgradeTo(address)' in source_code:
            return "uups"
        if re.search(PROXY_PATTERNS['EIP-1967'], source_code):
            return "eip1967"
        if re.search(r'\bdelegatecall\b', source_code):
            return "delegatecall"
        return "unknown"

    def _detect_functions_from_abi(self, abi):
        detected = []
        for item in abi:
            if item.get('type') == 'function':
                name = item.get('name', '')
                if not name:
                    continue
                name_lower = name.lower()

                if 'mint' in name_lower:
                    detected.append(name)
                elif 'burn' in name_lower:
                    detected.append(name)
                elif 'pause' in name_lower:
                    detected.append(name)
                elif 'blacklist' in name_lower:
                    detected.append(name)
                elif 'withdraw' in name_lower and 'owner' in name_lower:
                    detected.append(name)
                elif 'set' in name_lower and 'tax' in name_lower:
                    detected.append(name)
                elif 'transferownership' == name_lower:
                    detected.append(name)
                elif 'renounceownership' == name_lower:
                    detected.append(name)
                elif 'upgrade' in name_lower:
                    detected.append(name)
                elif 'configure' in name_lower and 'minter' in name_lower:
                    detected.append(name)

        return list(set(detected))

    def _analyze_permissions_and_risks(self, functions, source_code):
        flags = []
        functions_lower = [f.lower() for f in functions]

        if any('mint' in f for f in functions_lower):
            flags.append("Owner can mint unlimited supply")

        if any('pause' in f for f in functions_lower):
            flags.append("Trading can be paused by owner")

        if any('blacklist' in f for f in functions_lower):
            flags.append("Contract contains blacklist capabilities")

        if any('tax' in f for f in functions_lower):
            flags.append("Owner can adjust transaction taxes")

        if any('withdraw' in f for f in functions_lower):
            flags.append("Liquidity or funds withdrawal risk detected")

        if 'transferownership' in functions_lower or 'renounceownership' in functions_lower:
            flags.append("Owner privileges can be transferred or renounced")

        if any('upgrade' in f for f in functions_lower):
            flags.append("Contract supports upgrades (logic can be replaced)")

        if any('configureminter' in f for f in functions_lower):
            flags.append("Minter roles can be configured by admin")

        if source_code:
            if re.search(r"\bselfdestruct\b", source_code):
                flags.append("Contract contains SELFDESTRUCT (funds can be stolen/contract destroyed)")
            if re.search(r"\bdelegatecall\b", source_code):
                flags.append("Contract uses DELEGATECALL (risk of logic hijacking)")
            if re.search(r"\btx\.origin\b", source_code):
                flags.append("Contract references tx.origin (phishing vulnerability)")
            if re.search(r"\bblock\.timestamp\b", source_code) or re.search(r"\bnow\b", source_code):
                flags.append("Contract uses block.timestamp (potential timestamp manipulation)")
            if "mapping(address => bool) private _blacklisted" in source_code:
                if "Contract contains blacklist capabilities" not in flags:
                    flags.append("Contract contains blacklist capabilities")

        return flags

    def _calculate_risk_score(self, flags):
        score = 0
        risk_weights = {
            "Contract contains SELFDESTRUCT": 50,
            "Contract uses DELEGATECALL": 30,
            "Contract references tx.origin": 30,
            "Contract uses block.timestamp": 10,
            "Owner can mint unlimited supply": 40,
            "Trading can be paused by owner": 30,
            "Contract contains blacklist capabilities": 20,
            "Owner can adjust transaction taxes": 25,
            "Liquidity or funds withdrawal risk detected": 40,
            "Contract supports upgrades": 20,
            "Contract is an upgradeable proxy": 25,
            "Minter roles can be configured": 15,
        }

        for flag in flags:
            for key, weight in risk_weights.items():
                if key in flag:
                    score += weight
                    break

        return min(score, 100)
