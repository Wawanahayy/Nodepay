import asyncio
import random
import sys
import os
import aiohttp
import pytesseract
from PIL import Image
from io import BytesIO
from typing import List, Set, Dict, Any
from loguru import logger

# 设置 Tesseract 路径（Windows 用户需要）
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class Account:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

class Config:
    def __init__(self):
        self.max_concurrent_tasks = 3
        self.delay_before_start = {"min": 5, "max": 15}
        self.captcha = {
            "max_retries": 3,
            "recognition_threshold": 127,
            "expected_length": 4
        }
        self.api_base_url = "https://app.nodepay.ai"

class Bot:
    def __init__(self, account: Account, config: Config):
        self.account = account
        self.config = config
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def handle_captcha(self) -> str:
        try:
            await self.create_session()
            captcha_url = f"{self.config.api_base_url}/captcha"
            
            for attempt in range(self.config.captcha["max_retries"]):
                async with self.session.get(captcha_url) as response:
                    if response.status != 200:
                        logger.error(f"Captcha fetch failed, attempt {attempt + 1}/{self.config.captcha['max_retries']}")
                        continue
                    
                    image_data = await response.read()
                    image = Image.open(BytesIO(image_data))
                    
                    # 图片预处理
                    image = image.convert('L')
                    image = image.point(lambda x: 255 if x > self.config.captcha["recognition_threshold"] else 0)
                    
                    custom_config = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    captcha_text = pytesseract.image_to_string(image, config=custom_config).strip()
                    
                    if len(captcha_text) == self.config.captcha["expected_length"] and captcha_text.isalnum():
                        logger.info(f"Successfully recognized captcha: {captcha_text}")
                        return captcha_text
                    
                    logger.warning(f"Invalid captcha recognition result: {captcha_text}, retrying...")
            
            raise Exception("Failed to recognize captcha after maximum retries")
                
        except Exception as e:
            logger.error(f"Captcha handling error: {str(e)}")
            raise

    async def process_login(self) -> bool:
        try:
            await self.create_session()
            
            for attempt in range(self.config.captcha["max_retries"]):
                try:
                    captcha = await self.handle_captcha()
                    
                    login_data = {
                        'username': self.account.email,
                        'password': self.account.password,
                        'captcha': captcha
                    }
                    
                    async with self.session.post(f"{self.config.api_base_url}/login", json=login_data) as response:
                        response_data = await response.json()
                        
                        if response.status == 200 and response_data.get('success'):
                            logger.success(f"Successfully logged in: {self.account.email}")
                            return True
                        
                        if 'captcha' in response_data.get('message', '').lower():
                            logger.warning(f"Captcha verification failed, attempt {attempt + 1}/{self.config.captcha['max_retries']}")
                            continue
                        
                        logger.error(f"Login failed: {response_data.get('message', 'Unknown error')}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Login attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.config.captcha["max_retries"] - 1:
                        raise
                    
            return False
                    
        except Exception as e:
            logger.error(f"Login error for {self.account.email}: {str(e)}")
            return False

    async def process_farming(self) -> None:
        try:
            if await self.process_login():
                logger.info(f"Starting farming for {self.account.email}")
                # 在这里实现具体的farming逻辑
                await asyncio.sleep(random.randint(30, 60))  # 示例：随机等待
                logger.success(f"Farming completed for {self.account.email}")
            else:
                logger.error(f"Cannot start farming due to login failure: {self.account.email}")
        except Exception as e:
            logger.error(f"Farming error for {self.account.email}: {str(e)}")

class TaskManager:
    def __init__(self, config: Config):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self.accounts_with_delay: Set[str] = set()

    async def run_task_safe(self, account: Account, task_func) -> Any:
        async with self.semaphore:
            bot = Bot(account, self.config)
            try:
                if account.email not in self.accounts_with_delay:
                    delay = random.randint(
                        self.config.delay_before_start["min"],
                        self.config.delay_before_start["max"]
                    )
                    logger.info(f"Account: {account.email} | Initial delay: {delay} sec")
                    await asyncio.sleep(delay)
                    self.accounts_with_delay.add(account.email)

                return await task_func(bot)
            finally:
                await bot.close_session()

    async def run_farming(self, accounts: List[Account]) -> None:
        while True:
            tasks = []
            random.shuffle(accounts)
            
            for account in accounts:
                task = self.run_task_safe(account, lambda bot: bot.process_farming())
                tasks.append(task)

            await asyncio.gather(*tasks)
            logger.info("Completed one farming cycle, starting next...")
            await asyncio.sleep(10)

def load_accounts() -> List[Account]:
    """从指定路径加载账户信息"""
    accounts = []
    accounts_file = "/root/Nodepay/data/accounts.txt"
    
    try:
        with open(accounts_file, "r", encoding="utf-8") as f:
            for line in f:
                # 跳过空行和注释行
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                try:
                    # 假设格式为: email|password 或 email:password
                    if "|" in line:
                        email, password = line.split("|", 1)
                    else:
                        email, password = line.split(":", 1)
                        
                    email = email.strip()
                    password = password.strip()
                    
                    if email and password:  # 确保两个字段都不为空
                        accounts.append(Account(email, password))
                    else:
                        logger.warning(f"Skipping invalid account line: {line}")
                        
                except ValueError:
                    logger.error(f"Invalid format in line: {line}")
                    continue
                    
        logger.info(f"Successfully loaded {len(accounts)} accounts")
        return accounts
        
    except FileNotFoundError:
        logger.error(f"Accounts file not found: {accounts_file}")
        return []
    except Exception as e:
        logger.error(f"Error loading accounts: {str(e)}")
        return []

async def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 设置日志
    logger.add("bot.log", rotation="1 day", retention="7 days", level="INFO")
    
    # 确保账户文件目录存在
    os.makedirs("Nodepay/data", exist_ok=True)
    
    config = Config()
    accounts = load_accounts()
    
    if not accounts:
        logger.error("No accounts loaded!")
        return

    task_manager = TaskManager(config)
    
    try:
        await task_manager.run_farming(accounts)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
