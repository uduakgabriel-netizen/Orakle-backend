"""
Orakle Intelligence Platform — Price Service.

Provides real-time cryptocurrency price conversion using the CoinGecko API.
Supports ETH→USD and SOL→USD conversion with caching to minimize API calls.
"""

import logging
import time
import requests

logger = logging.getLogger('core')


class PriceService:
    """
    Real-time cryptocurrency price conversion service.

    Uses the CoinGecko public API (no key required) with in-memory caching
    to avoid rate limits. Cache TTL defaults to 60 seconds.
    """

    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
    CACHE_TTL = 60  # seconds

    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}

    def _get_price(self, coin_id, vs_currency='usd'):
        """
        Fetch the current price for a given coin from CoinGecko.

        Args:
            coin_id: CoinGecko coin identifier (e.g. 'ethereum', 'solana').
            vs_currency: Target fiat currency (default: 'usd').

        Returns:
            float: The current price, or 0.0 on failure.
        """
        cache_key = f"{coin_id}_{vs_currency}"
        now = time.time()

        # Return cached value if still valid
        if cache_key in self._cache:
            age = now - self._cache_timestamps.get(cache_key, 0)
            if age < self.CACHE_TTL:
                return self._cache[cache_key]

        try:
            response = requests.get(
                self.COINGECKO_URL,
                params={"ids": coin_id, "vs_currencies": vs_currency},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            price = float(data.get(coin_id, {}).get(vs_currency, 0.0))
            self._cache[cache_key] = price
            self._cache_timestamps[cache_key] = now
            logger.info("PriceService: %s/%s = %.2f", coin_id, vs_currency, price)
            return price
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("PriceService: failed to fetch %s price: %s", coin_id, exc)
            # Return stale cache if available, otherwise 0
            return self._cache.get(cache_key, 0.0)

    def get_eth_price_usd(self):
        """Return the current ETH price in USD."""
        return self._get_price('ethereum', 'usd')

    def get_sol_price_usd(self):
        """Return the current SOL price in USD."""
        return self._get_price('solana', 'usd')

    def convert_eth_to_usd(self, eth_amount):
        """
        Convert an ETH amount to its USD equivalent.

        Args:
            eth_amount: Amount of ETH (float or int).

        Returns:
            float: USD value, rounded to 2 decimal places.
        """
        try:
            eth_amount = float(eth_amount)
        except (ValueError, TypeError):
            return 0.0
        price = self.get_eth_price_usd()
        return round(eth_amount * price, 2)

    def convert_sol_to_usd(self, sol_amount):
        """
        Convert a SOL amount to its USD equivalent.

        Args:
            sol_amount: Amount of SOL (float or int).

        Returns:
            float: USD value, rounded to 2 decimal places.
        """
        try:
            sol_amount = float(sol_amount)
        except (ValueError, TypeError):
            return 0.0
        price = self.get_sol_price_usd()
        return round(sol_amount * price, 2)
