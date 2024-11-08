# config_loader.py
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Generator, Optional
import yaml
from loguru import logger
from better_proxy import Proxy
from models import Config, Account

@dataclass
class ConfigPaths:
    """配置文件路径"""
    BASE_PATH: Path = Path(os.getcwd()) / "config"
    DATA_PATH: Path = BASE_PATH / "data"
    SETTINGS_PATH: Path = BASE_PATH / "settings.yaml"
    
    def __post_init__(self):
        """确保必要的目录存在"""
        self.DATA_PATH.mkdir(parents=True, exist_ok=True)

class ConfigLoader:
    REQUIRED_DATA_FILES = ("accounts.txt", "proxies.txt")
    REQUIRED_PARAMS = {
        "threads": int,
        "keepalive_interval": int,
        "imap_settings": dict,
        "captcha_module": str,
        "delay_before_start": int,
    }

    def __init__(self):
        self.paths = ConfigPaths()
        
    def _read_file(self, file_path: Path, check_empty: bool = True, is_yaml: bool = False) -> List[str] | Dict:
        """读取文件内容"""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if check_empty and file_path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")

        try:
            if is_yaml:
                return yaml.safe_load(file_path.read_text(encoding="utf-8"))
            return [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        except Exception as e:
            raise ValueError(f"Failed to read {file_path}: {e}")

    def _validate_params(self, params: Dict) -> None:
        """验证配置参数"""
        for field, field_type in self.REQUIRED_PARAMS.items():
            if field not in params:
                raise ValueError(f"Missing required field: {field}")
            if not isinstance(params[field], field_type):
                raise TypeError(f"Field {field} must be of type {field_type.__name__}")

    def _get_proxies(self) -> List[Proxy]:
        """获取代理列表"""
        try:
            proxy_file = self.paths.DATA_PATH / "proxies.txt"
            proxies = self._read_file(proxy_file, check_empty=False)
            return [Proxy.from_str(line) for line in proxies] if proxies else []
        except Exception as e:
            logger.warning(f"Failed to load proxies: {e}")
            return []

    def _parse_account(self, line: str) -> Optional[Account]:
        """解析账户信息"""
        try:
            email, password = line.split(":")
            return Account(email=email.strip(), password=password.strip())
        except ValueError:
            logger.error(f"Invalid account format: {line}")
            return None

    def _get_accounts(self, file_name: str, proxies: List[Proxy]) -> List[Account]:
        """获取账户列表"""
        accounts_file = self.paths.DATA_PATH / file_name
        if not accounts_file.exists():
            return []

        accounts = []
        proxy_cycle = cycle(proxies) if proxies else None
        
        for line in self._read_file(accounts_file, check_empty=False):
            account = self._parse_account(line)
            if account:
                account.proxy = next(proxy_cycle) if proxy_cycle else None
                accounts.append(account)
        
        return accounts

    def _validate_domains(self, accounts: List[Account], domains: Dict[str, str]) -> None:
        """验证邮箱域名"""
        for account in accounts:
            domain = account.email.split("@")[1]
            if domain not in domains:
                raise ValueError(f"Unsupported email domain: {domain}")
            account.imap_server = domains[domain]

    def load(self) -> Config:
        """加载完整配置"""
        try:
            # 加载基本配置
            params = self._read_file(self.paths.SETTINGS_PATH, is_yaml=True)
            self._validate_params(params)

            # 加载代理和账户
            proxies = self._get_proxies()
            reg_accounts = self._get_accounts("register.txt", proxies)
            farm_accounts = self._get_accounts("farm.txt", proxies)

            if not reg_accounts and not farm_accounts:
                raise ValueError("No accounts found in data files")

            # 创建配置对象
            config = Config(
                **params,
                accounts_to_farm=farm_accounts,
                accounts_to_register=reg_accounts
            )

            # 验证域名
            if reg_accounts:
                self._validate_domains(reg_accounts, config.imap_settings)

            # 验证验证码配置
            self._validate_captcha_config(config)

            return config

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise

    def _validate_captcha_config(self, config: Config) -> None:
        """验证验证码配置"""
        if config.captcha_module == "2captcha" and not config.two_captcha_api_key:
            raise ValueError("2Captcha API key is missing")
        elif config.captcha_module == "anticaptcha" and not config.anti_captcha_api_key:
            raise ValueError("AntiCaptcha API key is missing")
