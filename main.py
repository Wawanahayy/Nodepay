import asyncio
import random
import sys
import os
import aiohttp
import pytesseract
from PIL import Image
from io import BytesIO

CurrentPath = os.path.dirname(__file__)
sys.path.append(CurrentPath)
sys.path.append(CurrentPath + "/models")
from typing import Callable, Coroutine, Any, List, Set

from loguru import logger
from loader import config, semaphore, file_operations
from models import Account
from utils import setup
from console import Console
from database import initialize_database

accounts_with_initial_delay: Set[str] = set()

class Bot:
    def __init__(self, account: Account):
        self.account = account
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
        """处理验证码识别"""
        try:
            await self.create_session()
            captcha_url = 'https://app.nodepay.ai/captcha'  # 根据实际URL调整
            
            async with self.session.get(captcha_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get captcha image, status: {response.status}")
                
                image_data = await response.read()
                
            # 保存验证码图片到内存
            image = Image.open(BytesIO(image_data))
            
            # 使用 pytesseract 识别验证码
            captcha_text = pytesseract.image_to_string(image).strip()
            logger.info(f"Recognized captcha: {captcha_text}")
            
            return captcha_text
            
        except Exception as e:
            logger.error(f"Captcha handling error: {str(e)}")
            raise

    async def process_login(self) -> bool:
        """处理登录流程"""
        try:
            await self.create_session()
            
            # 获取并识别验证码
            captcha = await self.handle_captcha()
            
            # 准备登录数据
            login_data = {
                'username': self.account.email,
                'password': self.account.password,
                'captcha': captcha
            }
            
            # 发送登录请求
            async with self.session.post('https://app.nodepay.ai/login', json=login_data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get('success'):
                        logger.success(f"Successfully logged in: {self.account.email}")
                        return True
                    else:
                        logger.error(f"Login failed: {response_data.get('message', 'Unknown error')}")
                        return False
                else:
                    logger.error(f"Login failed with status {response.status}: {self.account.email}")
                    return False
                
        except Exception as e:
            logger.error(f"Login error for {self.account.email}: {str(e)}")
            return False

    async def process_farming(self) -> None:
        """处理farming逻辑"""
        try:
            if await self.process_login():
                # 这里添加farming的具体逻辑
                logger.info(f"Starting farming for {self.account.email}")
                # ... farming logic ...
                pass
            else:
                logger.error(f"Cannot start farming due to login failure: {self.account.email}")
        except Exception as e:
            logger.error(f"Farming error: {str(e)}")

    async def process_registration(self) -> dict:
        """处理注册逻辑"""
        try:
            # 实现注册逻辑
            return {"status": "success", "message": "Registration completed"}
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def process_complete_tasks(self) -> dict:
        """处理任务完成逻辑"""
        try:
            if await self.process_login():
                # 实现任务完成逻辑
                return {"status": "success", "message": "Tasks completed"}
            return {"status": "error", "message": "Login failed"}
        except Exception as e:
            logger.error(f"Task completion error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def process_get_user_info(self) -> dict:
        """获取用户信息"""
        try:
            if await self.process_login():
                # 实现获取用户信息的逻辑
                return {"status": "success", "data": {"email": self.account.email}}
            return {"status": "error", "message": "Login failed"}
        except Exception as e:
            logger.error(f"Get user info error: {str(e)}")
            return {"status": "error", "message": str(e)}

async def run_module_safe(
        account: Account, process_func: Callable[[Bot], Coroutine[Any, Any, Any]]
) -> Any:
    global accounts_with_initial_delay

    async with semaphore:
        bot = Bot(account)
        try:
            if config.delay_before_start.min > 0:
                if process_func == process_farming and account.email not in accounts_with_initial_delay:
                    random_delay = random.randint(config.delay_before_start.min, config.delay_before_start.max)
                    logger.info(f"Account: {account.email} | Initial farming delay: {random_delay} sec")
                    await asyncio.sleep(random_delay)
                    accounts_with_initial_delay.add(account.email)
                elif process_func != process_farming:
                    random_delay = random.randint(config.delay_before_start.min, config.delay_before_start.max)
                    logger.info(f"Account: {account.email} | Sleep for {random_delay} sec")
                    await asyncio.sleep(random_delay)

            result = await process_func(bot)
            return result
        finally:
            await bot.close_session()

async def process_registration(bot: Bot) -> None:
    operation_result = await bot.process_registration()
    await file_operations.export_result(operation_result, "register")

async def process_farming(bot: Bot) -> None:
    await bot.process_farming()

async def process_export_stats(bot: Bot) -> None:
    data = await bot.process_get_user_info()
    await file_operations.export_stats(data)

async def process_complete_tasks(bot: Bot) -> None:
    operation_result = await bot.process_complete_tasks()
    await file_operations.export_result(operation_result, "tasks")

async def run_module(
        accounts: List[Account], process_func: Callable[[Bot], Coroutine[Any, Any, Any]]
) -> tuple[Any]:
    tasks = [run_module_safe(account, process_func) for account in accounts]
    return await asyncio.gather(*tasks)

async def farm_continuously(accounts: List[Account]) -> None:
    while True:
        random.shuffle(accounts)
        await run_module(accounts, process_farming)
        await asyncio.sleep(10)

def reset_initial_delays():
    global accounts_with_initial_delay
    accounts_with_initial_delay.clear()

async def run() -> None:
    await initialize_database()
    await file_operations.setup_files()
    reset_initial_delays()

    module_map = {
        "register": (config.accounts_to_register, process_registration),
        "farm": (config.accounts_to_farm, farm_continuously),
        "complete_tasks": (config.accounts_to_farm, process_complete_tasks),
        "export_stats": (config.accounts_to_farm, process_export_stats),
    }

    while True:
        Console().build()

        if config.module not in module_map:
            logger.error(f"Unknown module: {config.module}")
            break

        accounts, process_func = module_map[config.module]

        if not accounts:
            logger.error(f"No accounts for {config.module}")
            break

        if config.module == "farm":
            await process_func(accounts)
        else:
            await run_module(accounts, process_func)
            input("\n\nPress Enter to continue...")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    setup()
    asyncio.run(run())
