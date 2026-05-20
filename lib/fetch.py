import aiohttp
import logging
import requests


async def fetch(url: str):
    """Asynchronously fetch a URL and return parsed JSON."""
    logging.info(f"GET {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


def request(url: str):
    """Synchronously fetch a URL and return parsed JSON."""
    logging.info(f"GET {url}")
    return requests.get(url).json()
