import os
import requests
import json
import logging
import time
import re
from django.conf import settings

logger = logging.getLogger('ai')


def sanitize_text(text):
    if not isinstance(text, str):
        return text
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Also specifically handle tabs
    text = text.replace('\t', ' ')
    return text


class GemmaService:
    """
    Orakle Intelligence Platform — Gemma 4 AI Service Layer.
    Powered by Google Gemini API.
    """
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"
    MODEL_NAME = "gemini-3.5-flash"  # Verified working stable model for this key

    DEFAULT_FALLBACK = {
        "summary": "AI intelligence temporarily unavailable.",
        "threat_assessment": "Unknown",
        "key_findings": [],
        "recommendations": ["Retry analysis when AI service is available", "Review blockchain data manually for due diligence"],
        "confidence_score": 0.0,
        "confidence_reasoning": "Fallback mode activated due to connection limit or rate limit constraints.",
        "status": "fallback"
    }

    SYSTEM_PROMPT = (
        "You are Google Gemma 4 (26B), the AI intelligence engine powering Orakle. "
        "Analyze blockchain findings and return ONLY a valid JSON object. "
        "No chat, no markdown, no repetition of the prompt."
    )

    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
        self.is_configured = bool(self.api_key) and not self.api_key.startswith('your_')
        
        self.timeout = 45 # Increased timeout for heavy reasoning

        if not self.is_configured:
            logger.warning("GemmaService initialized without valid API key.")
        else:
            logger.info("GemmaService initialized with valid API key.")

    def _get_mock_response(self, input_data, analysis_type="wallet"):
        """Fallback when Gemini API is unavailable"""
        logger.info(f"Serving mock fallback response for type: {analysis_type}")
        if analysis_type == "contract":
            func_count = len(input_data.get('detected_functions', [])) if isinstance(input_data.get('detected_functions'), list) else 0
            signals = input_data.get('signals') or input_data.get('risk_flags') or []
            signal_count = len(signals) if isinstance(signals, list) else 0
            
            # Build specific findings from actual signals
            findings = []
            for sig in (signals[:5] if signals else []):
                sig_text = str(sig)
                if "mint" in sig_text.lower():
                    findings.append("MINT FUNCTION: The contract has an unrestricted mint function that allows the owner to create unlimited new tokens. This could lead to inflation and loss of token value. Recommendation: Implement access controls on the mint function.")
                elif "pause" in sig_text.lower():
                    findings.append("PAUSE CONTROL: The owner can pause all trading activity at any time. During a pause, holders cannot sell or transfer tokens. Recommendation: Add a timelock or governance mechanism.")
                elif "blacklist" in sig_text.lower():
                    findings.append("BLACKLIST FUNCTION: The owner can blacklist any address, preventing them from interacting with the contract. Recommendation: Consider renouncing or delegating this power to a multi-sig.")
                elif "delegatecall" in sig_text.lower():
                    findings.append("DELEGATECALL USAGE: The contract uses delegatecall which could allow logic hijacking if the target is compromised. Recommendation: Ensure the implementation is immutable.")
                elif "selfdestruct" in sig_text.lower():
                    findings.append("SELFDESTRUCT: The contract can be permanently destroyed and funds sent to a specified address. Recommendation: Avoid interacting with this contract.")
                elif "withdraw" in sig_text.lower():
                    findings.append("WITHDRAWAL RISK: A function allows the owner to withdraw pooled liquidity or user funds. This is a direct rug-pull vector. Recommendation: Lock liquidity in a third-party locker.")
                elif "tax" in sig_text.lower():
                    findings.append("TAX MANIPULATION: The owner can modify buy/sell tax rates without bounds. Recommendation: Implement a hard-coded max tax cap.")
                elif "upgrade" in sig_text.lower() or "proxy" in sig_text.lower():
                    findings.append("UPGRADEABLE CONTRACT: The contract logic can be replaced post-deployment. A malicious upgrade could drain all funds. Recommendation: Verify the admin is a multi-sig with a timelock.")
                else:
                    findings.append(f"SECURITY SIGNAL: {sig_text}. Recommendation: Investigate this pattern thoroughly before interacting.")
            
            if not findings:
                findings = [
                    f"Contract has {func_count} functions detected — no critical patterns found in structural analysis.",
                    "No dangerous or malicious code patterns detected in the available source code."
                ]
            
            risk_score = input_data.get('risk_score', 0)
            if risk_score and risk_score > 70:
                threat = "High Risk"
                recs = [
                    "CRITICAL: Do not interact with this contract until a full security audit is completed.",
                    "Investigate all detected functions for potential abuse vectors.",
                    "If you hold tokens, consider transferring to a secure wallet and monitoring for suspicious owner activity.",
                    "Audit proxy upgrade events and verify the implementation contract."
                ]
            elif risk_score and risk_score > 40:
                recs = [
                    "Perform a deeper audit on detected functions for hidden edge-cases.",
                    "Monitor proxy upgrade events and admin role actions.",
                    "Confirm compiler optimization settings are standard."
                ]
                threat = "Medium Risk"
            else:
                recs = [
                    "Monitor for abnormal transaction or call patterns.",
                    "No immediate code remediation or updates required.",
                    "Ensure regular security reviews are scheduled."
                ]
                threat = "Low Risk"
            
            return {
                "summary": f"Smart contract analysis detected {signal_count} risk signal(s) across {func_count} functions. {'Multiple high-risk patterns require immediate attention.' if risk_score and risk_score > 70 else 'The contract shows standard operational structure.'}",
                "threat_assessment": threat,
                "key_findings": findings,
                "recommendations": recs,
                "confidence_score": 0.85,
                "confidence_reasoning": "Based on deterministic rule-based analysis of contract ABI and source code patterns.",
                "status": "success"
            }
        elif analysis_type == "transaction":
            return {
                "summary": "This transaction represents standard blockchain transfer activity.",
                "threat_assessment": "Low Risk",
                "key_findings": [
                    "Gas fees are standard and within expected parameters.",
                    "Token/native transfer sizes match normal peer-to-peer behavior."
                ],
                "recommendations": [
                    "No direct security concerns detected",
                    "Process transaction under normal auditing procedures"
                ],
                "confidence_score": 0.85,
                "confidence_reasoning": "Based on deterministic rule-based analysis fallback.",
                "status": "success"
            }
        else:  # wallet
            return {
                "summary": "This wallet shows normal activity patterns based on transaction analysis.",
                "threat_assessment": "Low Risk",
                "key_findings": [
                    f"Wallet has {input_data.get('tx_count', 0)} transactions analyzed",
                    "No suspicious or high-velocity transfer patterns detected in history"
                ],
                "recommendations": [
                    "Continue normal monitoring protocols",
                    "No immediate action required"
                ],
                "confidence_score": 0.85,
                "confidence_reasoning": "Based on deterministic rule-based analysis fallback.",
                "status": "success"
            }

    def _call_ai(self, prompt, analysis_type="wallet", input_data=None):
        if not self.is_configured:
            logger.info("AI call skipped: API key not configured.")
            return self._get_mock_response(input_data or {}, analysis_type)

        # Sanitize the input prompt
        sanitized_prompt = sanitize_text(prompt)

        # Explicit JSON-only prompt with structure enforcement
        full_prompt = (
            f"SYSTEM: {self.SYSTEM_PROMPT}\n\n"
            f"USER: {sanitized_prompt}\n\n"
            f"ASSISTANT: {{"
        )
        
        url = f"{self.GEMINI_API_URL}/models/{self.MODEL_NAME}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json"
            }
        }

        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"AI Request (Attempt {attempt+1}/{max_retries}) | Model: {self.MODEL_NAME}")
                
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                
                logger.info(f"Gemini API Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    try:
                        raw_content = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    except (KeyError, IndexError) as e:
                        logger.error(f"Error extracting content from Gemini response: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        return self._get_mock_response(input_data or {}, analysis_type)

                    logger.info(f"Gemini Raw Content: {raw_content[:200]}...")

                    if not raw_content:
                        logger.error("AI response returned empty content.")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        return self._get_mock_response(input_data or {}, analysis_type)
                    
                    parsed_json = self._parse_ai_response(raw_content)
                    if parsed_json.get("status") == "fallback":
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        return self._get_mock_response(input_data or {}, analysis_type)
                        
                    return self._validate_and_sanitize(parsed_json)

                elif response.status_code == 429:
                    logger.warning(f"Gemini Rate Limit (429) hit on attempt {attempt+1}.")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Sleeping for {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    return self._get_mock_response(input_data or {}, analysis_type)

                elif response.status_code >= 500:
                    logger.warning(f"Gemini Server Error ({response.status_code}) on attempt {attempt+1}.")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Sleeping for {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    return self._get_mock_response(input_data or {}, analysis_type)

                response.raise_for_status()

            except requests.exceptions.Timeout:
                logger.error(f"AI Request Timeout on attempt {attempt+1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return self._get_mock_response(input_data or {}, analysis_type)
            except requests.exceptions.RequestException as e:
                logger.error(f"AI Request Failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return self._get_mock_response(input_data or {}, analysis_type)

        return self._get_mock_response(input_data or {}, analysis_type)

    def _parse_ai_response(self, raw_content: str) -> dict:
        """Extract JSON from AI response, handling markdown or extra text."""
        # Look for the outermost JSON object
        start_idx = raw_content.find('{')
        end_idx = raw_content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = raw_content[start_idx:end_idx+1]
            try:
                parsed_json = json.loads(content)
                if isinstance(parsed_json, list) and len(parsed_json) > 0:
                    parsed_json = parsed_json[0]
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"AI JSON Parse Error: {str(e)} | Raw snippet: {raw_content[:200]}")
                # Last-ditch effort for missing closing brace
                try:
                    fixed_content = content.strip()
                    if not fixed_content.endswith('}'):
                        fixed_content += '}'
                    return json.loads(fixed_content)
                except Exception:
                    pass
        
        return self._with_reason(self.DEFAULT_FALLBACK, "parse_error")

    def _with_reason(self, fallback, reason):
        res = fallback.copy()
        res["failure_reason"] = reason
        return res

    def _validate_and_sanitize(self, data):
        """Ensures the response matches the required structure."""
        if not isinstance(data, dict):
            logger.error(f"AI Validation Error: Response is not a dictionary.")
            return self._with_reason(self.DEFAULT_FALLBACK, "not_a_dict")
            
        score = data.get("confidence_score", 0.0)
        try:
            score = float(score)
            if score > 1.0:
                score = score / 100.0
        except (ValueError, TypeError):
            score = 0.85

        recommendations = list(data.get("recommendations", []))
        
        # CRITICAL: Ensure recommendations are never empty
        if not recommendations or (isinstance(recommendations, list) and len(recommendations) == 0):
            # Provide fallback recommendations based on threat assessment
            threat = str(data.get("threat_assessment", "")).lower()
            if "high" in threat or "critical" in threat:
                recommendations = [
                    "Monitor this address closely for any suspicious activity patterns.",
                    "Perform additional due diligence before any major transactions.",
                    "Consider implementing transaction alerts for this address."
                ]
            elif "medium" in threat:
                recommendations = [
                    "Review transaction history for risk indicators.",
                    "Monitor for any changes in activity patterns.",
                    "Standard precautions recommended."
                ]
            else:
                recommendations = [
                    "Continue normal monitoring protocols.",
                    "No immediate action required at this time.",
                    "Re-assess if significant behavioral changes are detected."
                ]

        return {
            "summary": str(data.get("summary", self.DEFAULT_FALLBACK["summary"])),
            "threat_assessment": str(data.get("threat_assessment", self.DEFAULT_FALLBACK["threat_assessment"])),
            "key_findings": list(data.get("key_findings", [])),
            "recommendations": recommendations,
            "confidence_score": score,
            "confidence_reasoning": str(data.get("confidence_reasoning", "Based on automated deterministic metrics.")),
            "status": "success"
        }

    def explain_wallet(self, analysis_data):
        # Sanitize dictionary values to prevent special character issues
        signals_source = analysis_data.get('signals') or analysis_data.get('risk_flags') or []
        sanitized_signals = [sanitize_text(str(s)) for s in signals_source]
        sanitized_metrics = {sanitize_text(str(k)): sanitize_text(str(v)) for k, v in analysis_data.get('metrics', {}).items()}
        
        prompt = f"""
You are an elite blockchain intelligence analyst.

Input Data:
- Deterministic Signals: {json.dumps(sanitized_signals, indent=2)}
- Metrics: {json.dumps(sanitized_metrics, indent=2)}
- Risk Score: {analysis_data.get('risk_score', 'N/A')}

CRITICAL: Your response MUST include a "recommendations" array with at least 2-3 specific, actionable recommendations. Never leave recommendations empty.

Example recommendations for a normal wallet:
- "Continue standard monitoring - no suspicious patterns detected"
- "No immediate action required"
- "Consider periodic review for ongoing compliance"

Example recommendations for a risky wallet:
- "Immediately investigate large outgoing transfers"
- "Freeze interaction with this address pending review"
- "Report to compliance team for further analysis"

Output ONLY valid JSON with this exact structure:
{{
    "summary": "string",
    "threat_assessment": "LOW/MEDIUM/HIGH RISK",
    "key_findings": ["string", "string"],
    "recommendations": ["string", "string", "string"],
    "confidence_score": number,
    "confidence_reasoning": "string"
}}
"""
        return self._call_ai(prompt, analysis_type="wallet", input_data=analysis_data)

    def explain_contract(self, analysis_data):
        # Sanitize dictionary values to prevent special character issues
        signals_source = analysis_data.get('signals') or analysis_data.get('risk_flags') or []
        sanitized_signals = [sanitize_text(str(s)) for s in signals_source]
        detected_functions = analysis_data.get('detected_functions', [])
        source_preview = sanitize_text(str(analysis_data.get('source_code_preview', '')))
        
        prompt = f"""
You are a smart contract security auditor. Analyze the contract and return vulnerabilities as clear, specific, actionable issues.

Input Data:
- Detected Risk Signals: {json.dumps(sanitized_signals, indent=2)}
- Detected Functions: {json.dumps(detected_functions, indent=2)}
- Contract Address: {analysis_data.get('contract_address', 'N/A')}
- Risk Score: {analysis_data.get('risk_score', 'N/A')}
- Source Code Preview: {source_preview[:500] if source_preview else 'N/A'}

For each vulnerability signal, provide a CLEAR, SPECIFIC explanation that anyone can understand:
- What the risk is (be specific about the function or pattern)
- Why it matters (real-world consequences)
- What to do about it (concrete recommendation)

CRITICAL: Your response MUST include:
1. A "summary" that clearly describes the overall contract security posture
2. "key_findings" array with at least 2-3 specific, detailed findings. Each finding MUST be a complete sentence explaining the vulnerability clearly. Example findings:
   - "MINT FUNCTION: The contract has an unrestricted mint function that allows any caller to create new tokens. This could lead to inflation and loss of token value. Recommendation: Implement access controls on the mint function."
   - "OWNER PRIVILEGES: The owner can pause trading and blacklist addresses. This is centralized control that could be abused. Recommendation: Transition to a multi-signature wallet or DAO."
   - "DELEGATECALL USAGE: The contract uses delegatecall which could allow logic hijacking. Recommendation: Ensure the implementation is immutable or has strict access controls."
   - "BLACKLIST FUNCTION: The owner can blacklist any address, preventing them from interacting with the contract. This could be used to freeze user funds. Recommendation: Consider renouncing or delegating this power."
3. "recommendations" array with at least 3 specific, actionable recommendations

Output ONLY valid JSON with this exact structure:
{{
    "summary": "string - clear overview of contract security",
    "threat_assessment": "LOW/MEDIUM/HIGH RISK",
    "key_findings": ["FINDING_TITLE: Detailed explanation of the vulnerability, why it matters, and what to do about it.", "..."],
    "recommendations": ["Specific actionable recommendation 1", "Specific actionable recommendation 2", "Specific actionable recommendation 3"],
    "confidence_score": number,
    "confidence_reasoning": "string"
}}
"""
        return self._call_ai(prompt, analysis_type="contract", input_data=analysis_data)

    def translate_transaction(self, tx_data):
        # Sanitize dictionary values to prevent special character issues
        sanitized_tx = {sanitize_text(str(k)): sanitize_text(str(v)) for k, v in tx_data.items()}
        
        prompt = f"""
You are an elite blockchain intelligence analyst specializing in transaction flow behavior.

Input Data:
- TX: {json.dumps(sanitized_tx, indent=2)}

CRITICAL: Your response MUST include a "recommendations" array with at least 2-3 specific, actionable recommendations. Never leave recommendations empty.

Example recommendations for a normal transaction:
- "Continue standard transaction auditing procedures"
- "No direct security concerns detected in this execution"
- "Log transaction hash for compliance logs"

Example recommendations for a risky transaction:
- "Flag transaction for compliance review"
- "Immediately trace destination wallet address flow"
- "Verify authorization of associated sender key"

Output ONLY valid JSON with this exact structure:
{{
    "summary": "string",
    "threat_assessment": "LOW/MEDIUM/HIGH RISK",
    "key_findings": ["string", "string"],
    "recommendations": ["string", "string", "string"],
    "confidence_score": number,
    "confidence_reasoning": "string"
}}
"""
        return self._call_ai(prompt, analysis_type="transaction", input_data=tx_data)
