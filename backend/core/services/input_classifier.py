"""
Universal Input Classifier

Deterministically classifies raw user input into one of:
    - ethereum_address  (0x + 40 hex chars)
    - ethereum_tx_hash  (0x + 64 hex chars)
    - solana_address    (base58, 32-44 chars)
    - solana_signature  (base58, 64-88 chars)
    - file_upload       (uploaded .sol file)
    - unknown

This module handles ONLY classification — no blockchain calls.
The universal router uses this to decide which analysis engine to invoke.
"""

import re
import logging

logger = logging.getLogger('core')

# Compiled patterns for performance
ETH_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')
ETH_TX_HASH_PATTERN = re.compile(r'^0x[a-fA-F0-9]{64}$')
SOLANA_BASE58_PATTERN = re.compile(r'^[1-9A-HJ-NP-Za-km-z]+$')

# Solana address: 32-44 base58 characters
SOLANA_ADDRESS_MIN_LEN = 32
SOLANA_ADDRESS_MAX_LEN = 44

# Solana signature: 64-88 base58 characters
SOLANA_SIGNATURE_MIN_LEN = 64
SOLANA_SIGNATURE_MAX_LEN = 88


class InputClassifier:
    """
    Classifies raw blockchain input into a known category.
    All methods are stateless and side-effect-free.
    """

    @staticmethod
    def classify(raw_input):
        """
        Classify a raw text input.

        Args:
            raw_input (str): The user-submitted string.

        Returns:
            dict: {
                "input_type": str,
                "value": str (cleaned),
                "chain": str or None
            }
        """
        if not raw_input or not isinstance(raw_input, str):
            return {
                "input_type": "unknown",
                "value": raw_input,
                "chain": None
            }

        cleaned = raw_input.strip()

        if not cleaned:
            return {
                "input_type": "unknown",
                "value": cleaned,
                "chain": None
            }

        # --- Ethereum TX Hash (check BEFORE address since it also starts with 0x) ---
        if ETH_TX_HASH_PATTERN.match(cleaned):
            logger.info("Input classified as ethereum_tx_hash: %s...%s", cleaned[:10], cleaned[-6:])
            return {
                "input_type": "ethereum_tx_hash",
                "value": cleaned,
                "chain": "ethereum"
            }

        # --- Ethereum Address ---
        if ETH_ADDRESS_PATTERN.match(cleaned):
            logger.info("Input classified as ethereum_address: %s", cleaned)
            return {
                "input_type": "ethereum_address",
                "value": cleaned,
                "chain": "ethereum"
            }

        # --- Solana (Base58 patterns) ---
        if SOLANA_BASE58_PATTERN.match(cleaned):
            length = len(cleaned)

            # Solana signature (longer)
            if SOLANA_SIGNATURE_MIN_LEN <= length <= SOLANA_SIGNATURE_MAX_LEN:
                # Could be either address or signature in the 64-88 range
                # Signatures are typically 87-88 chars; addresses are 32-44
                if length > SOLANA_ADDRESS_MAX_LEN:
                    logger.info("Input classified as solana_signature: %s...%s", cleaned[:10], cleaned[-6:])
                    return {
                        "input_type": "solana_signature",
                        "value": cleaned,
                        "chain": "solana"
                    }

            # Solana address
            if SOLANA_ADDRESS_MIN_LEN <= length <= SOLANA_ADDRESS_MAX_LEN:
                logger.info("Input classified as solana_address: %s", cleaned)
                return {
                    "input_type": "solana_address",
                    "value": cleaned,
                    "chain": "solana"
                }

            # Base58 but unusual length — could be a Solana signature in the 64-88 range
            if SOLANA_SIGNATURE_MIN_LEN <= length <= SOLANA_SIGNATURE_MAX_LEN:
                logger.info("Input classified as solana_signature (by length): %s...%s", cleaned[:10], cleaned[-6:])
                return {
                    "input_type": "solana_signature",
                    "value": cleaned,
                    "chain": "solana"
                }

        # --- Unknown ---
        logger.info("Input could not be classified: %s", cleaned[:50])
        return {
            "input_type": "unknown",
            "value": cleaned,
            "chain": None
        }

    @staticmethod
    def classify_file(uploaded_file):
        """
        Classify an uploaded file.

        Args:
            uploaded_file: Django UploadedFile object.

        Returns:
            dict: {
                "input_type": str,
                "filename": str,
                "chain": str or None,
                "error": str or None
            }
        """
        if not uploaded_file:
            return {
                "input_type": "unknown",
                "filename": None,
                "chain": None,
                "error": "No file uploaded."
            }

        filename = uploaded_file.name

        # Validate .sol extension
        if not filename.lower().endswith('.sol'):
            return {
                "input_type": "unknown",
                "filename": filename,
                "chain": None,
                "error": f"Unsupported file type: {filename}. Only .sol files are accepted."
            }

        # Validate file size (1MB limit)
        if uploaded_file.size > 1 * 1024 * 1024:
            return {
                "input_type": "unknown",
                "filename": filename,
                "chain": None,
                "error": "File size exceeds the 1MB limit."
            }

        # Validate UTF-8 encoding
        try:
            uploaded_file.seek(0)
            uploaded_file.read(1024).decode('utf-8')
            uploaded_file.seek(0)
        except (UnicodeDecodeError, AttributeError):
            return {
                "input_type": "unknown",
                "filename": filename,
                "chain": None,
                "error": "File is not valid UTF-8 encoded text."
            }

        logger.info("File classified as solidity_file: %s", filename)
        return {
            "input_type": "solidity_file",
            "filename": filename,
            "chain": "ethereum",
            "error": None
        }
