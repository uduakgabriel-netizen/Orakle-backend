"""
Ethereum Address Detection Service

Uses Web3.py and on-chain bytecode inspection (eth_getCode) to determine
whether an address is an EOA (wallet), a smart contract, or invalid.

This is the foundation of the universal intelligence router.
"""

import os
import logging

from web3 import Web3
from web3.exceptions import Web3Exception

logger = logging.getLogger('core')


class AddressDetectorService:
    """
    Production-grade address type detector using real blockchain bytecode inspection.

    Classification:
        - "invalid"   : Not a valid Ethereum address
        - "wallet"    : Valid address with no on-chain bytecode (EOA)
        - "contract"  : Valid address with deployed bytecode
    """

    def __init__(self):
        self.rpc_url = os.environ.get('ETH_RPC_URL', '')
        self._w3 = None

        if not self.rpc_url:
            logger.warning(
                "ETH_RPC_URL is not configured. "
                "On-chain address detection will be unavailable."
            )

    @property
    def w3(self):
        """Lazy-initialize Web3 connection."""
        if self._w3 is None:
            if not self.rpc_url:
                raise ConnectionError(
                    "ETH_RPC_URL is not configured. "
                    "Cannot connect to Ethereum node."
                )
            self._w3 = Web3(Web3.HTTPProvider(
                self.rpc_url,
                request_kwargs={'timeout': 15}
            ))
        return self._w3

    @staticmethod
    def validate_address(address):
        """
        Validate whether a string is a valid Ethereum address.

        Returns:
            bool: True if valid Ethereum address, False otherwise.
        """
        if not address or not isinstance(address, str):
            return False
        return Web3.is_address(address)

    @staticmethod
    def to_checksum(address):
        """
        Safely convert an address to its checksummed form.

        Returns:
            str or None: Checksummed address, or None if invalid.
        """
        try:
            return Web3.to_checksum_address(address)
        except (ValueError, Web3Exception):
            return None

    def detect_address_type(self, address):
        """
        Detect whether an Ethereum address is a wallet (EOA) or smart contract
        using on-chain bytecode inspection via eth_getCode.

        Args:
            address (str): The Ethereum address to inspect.

        Returns:
            dict: {
                "type": "invalid" | "wallet" | "contract",
                "address": str (checksummed) or original,
                "error": str or None
            }
        """
        # Step 1: Validate address format
        if not self.validate_address(address):
            logger.info("Address validation failed: %s", address)
            return {
                "type": "invalid",
                "address": address,
                "error": "Not a valid Ethereum address."
            }

        # Step 2: Convert to checksum
        checksum_address = self.to_checksum(address)
        if not checksum_address:
            logger.error("Checksum conversion failed for: %s", address)
            return {
                "type": "invalid",
                "address": address,
                "error": "Address checksum conversion failed."
            }

        # Step 3: Query on-chain bytecode
        try:
            bytecode = self.w3.eth.get_code(checksum_address)

            # eth_getCode returns b'\x00' or b'' for EOAs, non-empty for contracts
            if bytecode and bytecode != b'' and bytecode != b'\x00':
                logger.info(
                    "Contract detected at %s (bytecode length: %d bytes)",
                    checksum_address, len(bytecode)
                )
                return {
                    "type": "contract",
                    "address": checksum_address,
                    "error": None
                }
            else:
                logger.info("Wallet (EOA) detected at %s", checksum_address)
                return {
                    "type": "wallet",
                    "address": checksum_address,
                    "error": None
                }

        except ConnectionError as e:
            logger.error("RPC connection error during address detection: %s", e)
            return {
                "type": "invalid",
                "address": checksum_address,
                "error": f"Blockchain RPC unavailable: {str(e)}"
            }
        except Web3Exception as e:
            logger.error("Web3 error during bytecode inspection: %s", e)
            return {
                "type": "invalid",
                "address": checksum_address,
                "error": f"Blockchain query failed: {str(e)}"
            }
        except Exception as e:
            logger.error("Unexpected error during address detection: %s", e)
            return {
                "type": "invalid",
                "address": checksum_address,
                "error": "An unexpected error occurred during address detection."
            }
