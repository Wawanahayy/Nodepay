import asyncio
import time
import uuid
import json  # Importing json module
from loguru import logger
from fake_useragent import UserAgent
import cloudscraper
import os
import requests

# Constants
PING_INTERVAL = 60
RETRIES = 60
DELAY_BETWEEN_ACCOUNTS = 3  # Delay 3 detik antara akun

DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": [
        "http://13.215.134.222/api/network/ping",
        "http://18.139.20.49/api/network/ping",
        "http://52.74.35.173/api/network/ping",
        "http://52.77.10.116/api/network/ping",
        "http://3.1.154.253/api/network/ping"
    ]
}

# Fungsi untuk membaca token dari akun.txt
def load_token(token_file):
    try:
        with open(token_file, 'r') as file:
            token = file.read().strip()
        if not token:
            raise ValueError("Token file is empty")
        return token
    except Exception as e:
        logger.error(f"Failed to load token: {e}")
        raise SystemExit("Exiting due to failure in loading token")

# Proses untuk menjalankan akun secara bersamaan
async def render_profile_info(proxy, token, delay=0):
    # Fungsi untuk menangani pemrosesan akun
    try:
        if delay:
            await asyncio.sleep(delay)  # Menambahkan delay sebelum memulai
        np_session_info = load_session_info(proxy)

        if not np_session_info:
            # Generate new browser_id
            browser_id = uuid.uuid4()
            response = await call_api(DOMAIN_API["SESSION"], {}, proxy, token)
            valid_resp(response)
            account_info = response["data"]
            if account_info.get("uid"):
                save_session_info(proxy, account_info)
                await start_ping(proxy, token)
            else:
                handle_logout(proxy)
        else:
            account_info = np_session_info
            await start_ping(proxy, token)

    except Exception as e:
        logger.error(f"Error in render_profile_info for proxy {proxy}: {e}")

# Fungsi untuk memuat informasi sesi
def load_session_info(proxy):
    try:
        session_file = f"session_{proxy.replace(':', '_').replace('/', '_')}.json"  # File untuk setiap proxy
        if os.path.exists(session_file):
            with open(session_file, 'r') as file:
                session_data = json.load(file)
            return session_data
        return None  # Jika tidak ada informasi sesi
    except Exception as e:
        logger.error(f"Failed to load session info for proxy {proxy}: {e}")
        return None

# Fungsi untuk menyimpan sesi
def save_session_info(proxy, data):
    try:
        session_file = f"session_{proxy.replace(':', '_').replace('/', '_')}.json"
        with open(session_file, 'w') as file:
            json.dump(data, file, indent=4)  # Simpan session info dalam format JSON
        logger.info(f"Session info saved for proxy {proxy}")
    except Exception as e:
        logger.error(f"Failed to save session info for proxy {proxy}: {e}")

# Fungsi untuk melakukan ping secara berkelanjutan
async def start_ping(proxy, token):
    try:
        while True:
            await ping(proxy, token)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        logger.info(f"Ping task for proxy {proxy} was cancelled")
    except Exception as e:
        logger.error(f"Error in start_ping for proxy {proxy}: {e}")

# Fungsi untuk memanggil API
async def call_api(url, data, proxy, token):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
headers = {
    "Authorization": f"Bearer {token.strip()}",  # Strip any unwanted whitespace or newline
    "Content-Type": "application/json",
    "User-Agent": random_user_agent,
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://app.nodepay.ai",
}


    try:
        # Mengonfigurasi proxy SOCKS5
        proxy_url = f"socks5://{proxy}"

        # Menggunakan cloudscraper tanpa memberikan session
        scraper = cloudscraper.create_scraper()

        # Menetapkan proxy untuk scraper
        scraper.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }

        # Melakukan request ke API
        response = scraper.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        return valid_resp(response.json())

    except Exception as e:
        logger.error(f"Error during API call: {e}")
        raise ValueError(f"Failed API call to {url}")


# Fungsi untuk memuat proxy dari file
def load_proxies(proxy_file):
    try:
        with open(proxy_file, 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        raise SystemExit("Exiting due to failure in loading proxies")

# Fungsi untuk validasi respons dari API
def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp

# Fungsi untuk menangani login/logout
def handle_logout(proxy):
    logger.info(f"Logged out and cleared session info for proxy {proxy}")

# Fungsi utama untuk menjalankan akun secara bersamaan
async def main():
    all_proxies = load_proxies('proxy.txt')  # Memuat daftar proxy dari file
    token = load_token('akun.txt')  # Membaca token dari akun.txt
    if not token:
        print("Token cannot be empty. Exiting the program.")
        exit()

    tasks = []
    for i, proxy in enumerate(all_proxies[:100]):
        # Menambahkan task untuk setiap proxy dengan delay 3 detik antara akun
        task = asyncio.create_task(render_profile_info(proxy, token, delay=i * DELAY_BETWEEN_ACCOUNTS))
        tasks.append(task)

    # Menunggu semua task selesai
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
