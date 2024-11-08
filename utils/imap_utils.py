# imap_utils.py
import re
import asyncio
from typing import Optional, List
from loguru import logger
from imap_tools import MailBox, AND
from contextlib import contextmanager

# 常量配置
SPAM_FOLDERS = ("SPAM", "Spam", "spam", "Junk", "junk")
VERIFICATION_LINK_PATTERN = r"https://www\.aeropres\.in/chromeapi/dawn/v1/user/verifylink\?key=[a-f0-9-]+"
SENDER_EMAIL = "hello@dawninternet.com"

class ImapClient:
    def __init__(self, imap_server: str):
        self.imap_server = imap_server

    @contextmanager
    def _get_mailbox(self, email: str, password: str) -> MailBox:
        """安全的邮箱连接上下文管理器"""
        mailbox = MailBox(self.imap_server).login(email, password)
        try:
            yield mailbox
        finally:
            mailbox.logout()

    async def check_if_email_valid(self, email: str, password: str) -> bool:
        """验证邮箱登录是否有效"""
        logger.info(f"Account: {email} | Checking if email is valid...")
        
        try:
            async with asyncio.timeout(30):  # 添加超时控制
                await asyncio.to_thread(
                    lambda: self._get_mailbox(email, password).__enter__()
                )
            return True
        except Exception as error:
            logger.error(f"Account: {email} | Email is invalid (IMAP): {error}")
            return False

    async def check_email_for_link(
        self,
        email: str,
        password: str,
        max_attempts: int = 8,
        delay_seconds: int = 5,
    ) -> Optional[str]:
        """检查邮件中的验证链接"""
        logger.info(f"Account: {email} | Checking email for link...")

        try:
            # 检查收件箱
            link = await self._check_inbox_with_retry(
                email, password, max_attempts, delay_seconds
            )
            if link:
                return link

            # 如果收件箱没找到，检查垃圾邮件文件夹
            logger.warning(
                f"Account: {email} | Link not found after {max_attempts} attempts, searching in spam folders..."
            )
            return await self._check_spam_folders(email, password)

        except Exception as error:
            logger.error(f"Account: {email} | Failed to check email for link: {error}")
            return None

    async def _check_inbox_with_retry(
        self, email: str, password: str, max_attempts: int, delay_seconds: int
    ) -> Optional[str]:
        """重试检查收件箱"""
        for attempt in range(max_attempts):
            try:
                link = await asyncio.to_thread(
                    lambda: self._search_for_link(email, password)
                )
                if link:
                    return link

                if attempt < max_attempts - 1:
                    logger.info(
                        f"Account: {email} | Link not found. Waiting {delay_seconds} seconds before next attempt..."
                    )
                    await asyncio.sleep(delay_seconds)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay_seconds)
        return None

    async def _check_spam_folders(self, email: str, password: str) -> Optional[str]:
        """检查所有垃圾邮件文件夹"""
        for spam_folder in SPAM_FOLDERS:
            try:
                link = await asyncio.to_thread(
                    lambda: self._search_for_link(email, password, spam_folder)
                )
                if link:
                    return link
            except Exception as e:
                logger.error(f"Failed to check spam folder {spam_folder}: {e}")
        return None

    def _search_for_link(
        self, email: str, password: str, folder: Optional[str] = None
    ) -> Optional[str]:
        """在指定文件夹中搜索链接"""
        with self._get_mailbox(email, password) as mailbox:
            if folder and mailbox.folder.exists(folder):
                mailbox.folder.set(folder)
            
            messages = mailbox.fetch(AND(from_=SENDER_EMAIL))
            for msg in messages:
                body = msg.text or msg.html
                if body:
                    match = re.search(VERIFICATION_LINK_PATTERN, body)
                    if match:
                        return match.group(0)
        return None
