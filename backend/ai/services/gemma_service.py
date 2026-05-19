import os
import requests
import json
import logging

logger = logging.getLogger('ai')


class GemmaService:
    """
    Service to interact with AI via OpenRouter.
    Gracefully degrades when API key is missing or service is unavailable.
    """
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "google/gemma-2-9b-it"
    FALLBACK_MESSAGE = "AI analysis temporarily unavailable. Deterministic analysis results remain valid."

    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY', '')
        self.is_configured = bool(self.api_key) and not self.api_key.startswith('your_')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://orakle.intelligence",
            "X-Title": "Orakle Intelligence",
            "Content-Type": "application/json"
        }
        self.timeout = 20

        if not self.is_configured:
            logger.warning("GemmaService initialized without valid API key. AI features will return fallback responses.")

    def _call_ai(self, prompt, system_prompt="You are Orakle AI, an elite blockchain security analyst. Provide concise, analytical, cybersecurity-focused intelligence reports without fabricating data, calculating risk scores, or hallucinating facts."):
        if not self.is_configured:
            logger.info("AI call skipped: API key not configured.")
            return self.FALLBACK_MESSAGE

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if not content:
                logger.error("AI response returned empty content.")
                return self.FALLBACK_MESSAGE
            return content
        except requests.exceptions.Timeout:
            logger.error("AI service request timed out after %ds.", self.timeout)
            return self.FALLBACK_MESSAGE
        except requests.exceptions.HTTPError as e:
            logger.error("AI service HTTP error: %s", e)
            return self.FALLBACK_MESSAGE
        except requests.exceptions.ConnectionError as e:
            logger.error("AI service connection error: %s", e)
            return self.FALLBACK_MESSAGE
        except requests.exceptions.RequestException as e:
            logger.error("AI service request error: %s", e)
            return self.FALLBACK_MESSAGE
        except (KeyError, IndexError, TypeError) as e:
            logger.error("AI service response parsing error: %s", e)
            return self.FALLBACK_MESSAGE

    def explain_wallet(self, structured_data):
        prompt = f"""
Analyze the following deterministic wallet data.
Provide a concise, professional cybersecurity assessment.
Do NOT invent signals or metrics. Do NOT calculate a risk score (it is already provided if applicable).

Data points:
{json.dumps(structured_data, indent=2)}

Output format (in plain text, no markdown headers if possible, just clear paragraphs):
1. Behavioral Summary: Explain the wallet's main activity pattern based ONLY on the metrics and signals provided.
2. Security Assessment: Detail any suspicious activities or risks based on the provided signals.
3. Recommendations: Actionable advice for users interacting with this wallet.
"""
        return self._call_ai(prompt)

    def explain_contract(self, structured_data):
        prompt = f"""
Analyze the following deterministic smart contract analysis results.
Provide a concise, professional security assessment.
Do NOT invent signals or capabilities. Do NOT calculate a risk score.

Data points:
{json.dumps(structured_data, indent=2)}

Output format:
1. Contract Architecture Summary: Describe what this contract seems to do based on the detected functions.
2. Exploit & Ownership Risks: Detail the specific dangers of the provided risk flags.
3. Recommendations: Actionable security advice regarding this contract.
"""
        return self._call_ai(prompt)

    def translate_transaction(self, structured_data):
        prompt = f"""
Analyze this deterministic blockchain transaction data.
Explain it in clear, professional English for a user. Focus on security and clarity.

Data points:
{json.dumps(structured_data, indent=2)}

Output format:
1. Transaction Summary: What occurred in this transaction?
2. Security Observations: Any unusual elements or risks based on the data.
"""
        return self._call_ai(prompt)
