# file_utils.py
import asyncio
import aiofiles
from pathlib import Path
from aiocsv import AsyncWriter
from loguru import logger  # 添加日志支持
from models import ModuleType, OperationResult, StatisticData

class FileOperations:
    def __init__(self, base_path: str = "./results"):
        self.base_path = Path(base_path)
        self.lock = asyncio.Lock()
        # ... existing module_paths code ...

    async def setup_files(self):
        """Initialize directory structure and files"""
        try:
            self.base_path.mkdir(exist_ok=True)
            for module_paths in self.module_paths.values():
                for path in module_paths.values():
                    path.touch(exist_ok=True)

            # 初始化统计文件表头
            await self._initialize_stats_file()
            logger.info(f"File structure initialized at {self.base_path}")
        except Exception as e:
            logger.error(f"Failed to setup files: {e}")
            raise

    async def _initialize_stats_file(self):
        """Initialize stats file with headers"""
        headers = [
            "Email",
            "Referral Code",
            "Points",
            "Referral Points",
            "Total Points",
            "Registration Date",
            "Completed Tasks"
        ]
        async with aiofiles.open(self.module_paths["stats"]["base"], "w") as f:
            writer = AsyncWriter(f)
            await writer.writerow(headers)

    async def export_result(self, result: OperationResult, module: ModuleType):
        """Export operation results to file"""
        if module not in self.module_paths:
            logger.error(f"Unknown module: {module}")
            raise ValueError(f"Unknown module: {module}")

        file_path = self.module_paths[module]["success" if result["status"] else "failed"]
        async with self.lock:
            try:
                async with aiofiles.open(file_path, "a") as file:
                    line = f"{result['identifier']}:{result['data']}\n"
                    await file.write(line)
                logger.debug(f"Exported result to {file_path}")
            except IOError as e:
                logger.error(f"Error writing to {file_path}: {e}")
                raise

    async def export_stats(self, data: StatisticData):
        """Export statistics data to CSV"""
        if not self._validate_stats_data(data):
            logger.warning("Invalid or incomplete stats data")
            return

        file_path = self.module_paths["stats"]["base"]
        async with self.lock:
            try:
                async with aiofiles.open(file_path, mode="a", newline="") as f:
                    writer = AsyncWriter(f)
                    row = self._prepare_stats_row(data)
                    await writer.writerow(row)
                logger.debug(f"Exported stats to {file_path}")
            except IOError as e:
                logger.error(f"Error writing stats: {e}")
                raise

    def _validate_stats_data(self, data: StatisticData) -> bool:
        """Validate statistics data completeness"""
        return bool(
            data 
            and data.get("referralPoint") 
            and data.get("rewardPoint")
        )

    def _prepare_stats_row(self, data: StatisticData) -> list:
        """Prepare row data for stats CSV"""
        reward_point = data["rewardPoint"]
        referral_point = data["referralPoint"]
        
        total_points = (
            float(reward_point["points"]) 
            + float(referral_point["commission"])
        )
        
        tasks_completed = all([
            reward_point["twitter_x_id_points"] == 5000,
            reward_point["discordid_points"] == 5000,
            reward_point["telegramid_points"] == 5000
        ])

        return [
            referral_point["email"],
            referral_point["referralCode"],
            reward_point["points"],
            referral_point["commission"],
            total_points,
            reward_point["registerpointsdate"],
            tasks_completed
        ]
