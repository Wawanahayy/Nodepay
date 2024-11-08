import asyncio
from collections import deque
from better_proxy import Proxy
from core.utils.file_manager import file_to_list

proxies = deque()

lock = asyncio.Lock()


def load_proxy(proxy_path):
    global proxies
    proxies = deque([Proxy.from_str(proxy).as_url for proxy in file_to_list(proxy_path)])


async def get_proxy():
    """Return the first available proxy."""
    global proxies

    async with lock:
        if proxies:
            proxy = proxies.popleft()
            return proxy
        return None


async def release_proxy(proxy: str):
    """Release the proxy back into the available pool."""
    global proxies

    async with lock:
        proxies.append(proxy)
