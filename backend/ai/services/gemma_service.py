import os
import requests
import json
import logging
import time
from django.conf import settings

logger = logging.getLogger('ai')


class GemmaService:
    """
    Orakle Intelligence Platform — Gemma 4 AI Service Layer.
    Powered by OpenRouter.
    """
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL_NAME = "google/gemma-4-26b-a4b-it:free"
    
    DEFAULT_FALLBACK = {
        "summary": "AI intelligence temporarily unavailable.",
        "threat_assessment": "Unknown",
        "key_findings": [],
        "recommendations": [],
        "confidence_score": 0,
        "status": "fallback"
    }

    SYSTEM_PROMPT = (
        "You are Orakle AI, an elite blockchain intelligence analyst, crypto threat investigator, "
        "and forensic blockchain reasoning engine. Your goal is to explain deterministic blockchain "
        "findings with enterprise-grade clarity. "
        "Rules:\n"
        "1. NEVER hallucinate risk scores or fabricate blockchain data.\n"
        "2. Explain findings clearly and simplify technical concepts for normal users.\n"
        "3. Remain analytical, professional, and security-oriented. Avoid hype or speculation.\n"
        "4. Return ONLY valid JSON in the requested format.\n"
        "5. The deterministic engine has already detected signals; you interpret their significance."
    )

    def __init__(self):
        self.api_key = getattr(settings, 'OPENROUTER_API_KEY', os.environ.get('OPENROUTER_API_KEY', ''))
        self.is_configured = bool(self.api_key) and not self.api_key.startswith('your_')
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Orakle Intelligence Platform"
        }
        self.timeout = 45 # Increased timeout for heavy reasoning

        if not self.is_configured:
            logger.warning("GemmaService initialized without valid API key.")

    def _call_ai(self, prompt):
        if not self.is_configured:
            logger.info("AI call skipped: API key not configured.")
            return self._with_reason(self.DEFAULT_FALLBACK, "missing_api_key")

        payload = {
            "model": self.MODEL_NAME,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"AI Request (Attempt {attempt+1}/{max_retries}) | Model: {self.MODEL_NAME}")
                
                response = requests.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                logger.info(f"OpenRouter Status: {response.status_code}")
                
                if response.status_code == 429:
                    logger.warning(f"OpenRouter Rate Limit (429) hit on attempt {attempt+1}.")
                    if attempt < max_retries - 1:
                        sleep_time = 5 * (attempt + 1)
                        logger.info(f"Sleeping for {sleep_time}s before retry...")
                        time.sleep(sleep_time)
                        continue
                    return self._with_reason(self.DEFAULT_FALLBACK, "rate_limited")

                response.raise_for_status()
                data = response.json()
                
                raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                logger.info(f"OpenRouter Raw Content: {raw_content[:200]}...")

                if not raw_content:
                    logger.error("AI response returned empty content.")
                    return self._with_reason(self.DEFAULT_FALLBACK, "empty_response")
                
                try:
                    content = raw_content
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    
                    parsed_json = json.loads(content)
                    
                    # Handle if AI returns a list containing the object
                    if isinstance(parsed_json, list) and len(parsed_json) > 0:
                        parsed_json = parsed_json[0]
                        
                    return self._validate_and_sanitize(parsed_json)
                except json.JSONDecodeError as e:
                    logger.error(f"AI JSON Parse Error: {str(e)} | Raw: {raw_content}")
                    return self._with_reason(self.DEFAULT_FALLBACK, "parse_error")

            except requests.exceptions.Timeout:
                logger.error(f"AI Request Timeout on attempt {attempt+1}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return self._with_reason(self.DEFAULT_FALLBACK, "timeout")
            except requests.exceptions.RequestException as e:
                logger.error(f"AI Request Failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return self._with_reason(self.DEFAULT_FALLBACK, "request_failed")

        return self.DEFAULT_FALLBACK

    def _with_reason(self, fallback, reason):
        res = fallback.copy()
        res["failure_reason"] = reason
        return res

    def _validate_and_sanitize(self, data):
        """Ensures the response matches the required structure."""
        if not isinstance(data, dict):
            logger.error(f"AI Validation Error: Response is not a dictionary. Type: {type(data)} | Value: {data}")
            return self._with_reason(self.DEFAULT_FALLBACK, "not_a_dict")
            
        return {
            "summary": str(data.get("summary", self.DEFAULT_FALLBACK["summary"])),
            "threat_assessment": str(data.get("threat_assessment", self.DEFAULT_FALLBACK["threat_assessment"])),
            "key_findings": list(data.get("key_findings", [])),
            "recommendations": list(data.get("recommendations", [])),
            "confidence_score": data.get("confidence_score", 0),
            "status": "success"
        }

    def explain_wallet(self, analysis_data):
        prompt = f"""
Analyze the following Ethereum/Solana wallet intelligence data.
Deterministic Signals: {json.dumps(analysis_data.get('signals', []), indent=2)}
Metrics: {json.dumps(analysis_data.get('metrics', {}), indent=2)}
Risk Score: {analysis_data.get('risk_score', 'N/A')}

Explain this wallet's behavior and risks for a professional investigator.
Return JSON:
{{
  "summary": "overview of wallet behavior",
  "threat_assessment": "High/Medium/Low with brief reason",
  "key_findings": ["finding 1", "finding 2"],
  "recommendations": ["advice 1", "advice 2"],
  "confidence_score": 95
}}
"""
        return self._call_ai(prompt)

    def explain_contract(self, analysis_data):
        prompt = f"""
Analyze the following Smart Contract security data.
Detected Vulnerabilities/Flags: {json.dumps(analysis_data.get('signals', []), indent=2)}
Contract Address: {analysis_data.get('contract_address', 'N/A')}
Risk Score: {analysis_data.get('risk_score', 'N/A')}

Explain the implications of delegatecall, selfdestruct, minting, or ownership risks if present.
Return JSON:
{{
  "summary": "architectural and security overview",
  "threat_assessment": "Critical/High/Medium/Low",
  "key_findings": ["risk 1", "risk 2"],
  "recommendations": ["investor advice 1", "developer advice 2"],
  "confidence_score": 98
}}
"""
        return self._call_ai(prompt)

    def translate_transaction(self, tx_data):
        prompt = f"""
Translate this blockchain transaction into human-readable intelligence.
TX Data: {json.dumps(tx_data, indent=2)}

Explain what occurred, who is involved, and any risk implications.
Return JSON:
{{
  "summary": "Plain English explanation of the action",
  "threat_assessment": "Safe/Suspicious/Malicious",
  "key_findings": ["insight 1", "insight 2"],
  "recommendations": ["actionable advice"],
  "confidence_score": 90
}}
"""
        return self._call_ai(prompt)
