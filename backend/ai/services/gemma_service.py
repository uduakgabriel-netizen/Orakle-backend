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
    Powered by Google Gemini API.
    """
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"
    MODEL_NAME = "gemma-4-26b-a4b-it"  # Fallback: "gemini-1.5-flash"
    
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

    def _call_ai(self, prompt):
        if not self.is_configured:
            logger.info("AI call skipped: API key not configured.")
            return self._with_reason(self.DEFAULT_FALLBACK, "missing_api_key")

        # Explicit JSON-only prompt with structure enforcement
        full_prompt = (
            f"SYSTEM: {self.SYSTEM_PROMPT}\n\n"
            f"USER: {prompt}\n\n"
            f"ASSISTANT: {{"
        )
        
        url = f"{self.GEMINI_API_URL}/models/{self.MODEL_NAME}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json"
            }
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"AI Request (Attempt {attempt+1}/{max_retries}) | Model: {self.MODEL_NAME}")
                
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                
                logger.info(f"Gemini API Status: {response.status_code}")
                
                if response.status_code == 429:
                    logger.warning(f"Gemini Rate Limit (429) hit on attempt {attempt+1}.")
                    if attempt < max_retries - 1:
                        sleep_time = 5 * (attempt + 1)
                        logger.info(f"Sleeping for {sleep_time}s before retry...")
                        time.sleep(sleep_time)
                        continue
                    return self._with_reason(self.DEFAULT_FALLBACK, "rate_limited")

                if response.status_code >= 500:
                    logger.warning(f"Gemini Server Error ({response.status_code}) on attempt {attempt+1}.")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return self._with_reason(self.DEFAULT_FALLBACK, "server_error")

                response.raise_for_status()
                data = response.json()
                
                try:
                    raw_content = data['candidates'][0]['content']['parts'][0]['text'].strip()
                except (KeyError, IndexError) as e:
                    logger.error(f"Error extracting content from Gemini response: {e}")
                    return self._with_reason(self.DEFAULT_FALLBACK, "malformed_response")

                logger.info(f"Gemini Raw Content: {raw_content[:200]}...")

                if not raw_content:
                    logger.error("AI response returned empty content.")
                    return self._with_reason(self.DEFAULT_FALLBACK, "empty_response")
                
                parsed_json = self._parse_ai_response(raw_content)
                if parsed_json.get("status") == "fallback":
                    if attempt < max_retries - 1:
                        continue
                    return parsed_json
                    
                return self._validate_and_sanitize(parsed_json)

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
        prompt = f"""
Analyze this wallet intelligence data and return ONLY a valid JSON object.
No introductory text. No prompt echoing.

Input Data:
- Deterministic Signals: {json.dumps(analysis_data.get('signals', []), indent=2)}
- Metrics: {json.dumps(analysis_data.get('metrics', {}), indent=2)}
- Risk Score: {analysis_data.get('risk_score', 'N/A')}

CRITICAL: Recommendations MUST ALWAYS have at least 1 item. Never return empty recommendations array.
If wallet is low-risk, provide monitoring recommendations.
If wallet is medium-risk, provide specific warnings.
If wallet is high-risk, provide urgent action items.

Structure:
{{
  "summary": "string",
  "threat_assessment": "string",
  "key_findings": ["string"],
  "recommendations": ["string"],
  "confidence_score": number,
  "confidence_reasoning": "string"
}}
"""
        return self._call_ai(prompt)

    def explain_contract(self, analysis_data):
        prompt = f"""
Analyze this smart contract data and return ONLY a valid JSON object.
No introductory text. No prompt echoing.

Input Data:
- Signals: {json.dumps(analysis_data.get('signals', []), indent=2)}
- Address: {analysis_data.get('contract_address', 'N/A')}
- Risk Score: {analysis_data.get('risk_score', 'N/A')}

CRITICAL: Recommendations MUST ALWAYS have at least 1 item. Never return empty recommendations array.
If contract is low-risk, provide monitoring recommendations.
If contract is medium-risk, provide specific cautions.
If contract is high-risk, provide urgent remediation steps.

Structure:
{{
  "summary": "string",
  "threat_assessment": "string",
  "key_findings": ["string"],
  "recommendations": ["string"],
  "confidence_score": number,
  "confidence_reasoning": "string"
}}
"""
        return self._call_ai(prompt)

    def translate_transaction(self, tx_data):
        prompt = f"""
Translate this blockchain transaction and return ONLY a valid JSON object.
No introductory text. No prompt echoing.

Input Data:
- TX: {json.dumps(tx_data, indent=2)}

CRITICAL: Recommendations MUST ALWAYS have at least 1 item. Never return empty recommendations array.
Provide actionable recommendations based on the transaction type and risk indicators.

Structure:
{{
  "summary": "string",
  "threat_assessment": "string",
  "key_findings": ["string"],
  "recommendations": ["string"],
  "confidence_score": number,
  "confidence_reasoning": "string"
}}
"""
        return self._call_ai(prompt)
