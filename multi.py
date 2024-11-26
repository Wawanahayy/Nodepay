import asyncio
import time
import uuid
from loguru import logger
from fake_useragent import UserAgent
import cloudscraper
import os
import json

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

# Fungsi untuk menyimpan sesi
def save_session_info(proxy, data):
    session_file = f"session_{proxy}.json"  # File sesi berdasarkan proxy
    try:
        with open(session_file, 'w') as file:
            json.dump(data, file, indent=4)  # Menyimpan data sesi dalam format JSON
    except Exception as e:
        logger.error(f"Failed to save session data for proxy {proxy}: {e}")

# Fungsi untuk memanggil API
async def call_api(url, data, proxy, token):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": random_user_agent,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://app.nodepay.ai",
    }

    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.post(url, json=data, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=30)
        response.raise_for_status()
        return valid_resp(response.json())
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        raise ValueError(f"Failed API call to {url}")

# Fungsi untuk memvalidasi respons dari API
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
