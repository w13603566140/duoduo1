"""
Windows 任务计划程序助手 - 注册/删除每日定时任务
"""
import os
import sys
import subprocess
from utils.logger import logger

TASK_NAME = "Duoduo1_PDD_Scrape"


def register_windows_task(python_path: str = None, script_path: str = None):
    """
    注册 Windows 每日定时任务。
    使用 schtasks.exe 创建任务，每天指定时间运行 main.py --run-once。
    """
    if python_path is None:
        python_path = sys.executable

    if script_path is None:
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")

    # 默认凌晨2点
    from config import config
    cron_parts = config.scrape_cron.split()
    hour = cron_parts[1].zfill(2) if len(cron_parts) >= 2 else "02"
    minute = cron_parts[0].zfill(2) if len(cron_parts) >= 1 else "00"

    cmd = [
        "schtasks",
        "/Create",
        "/SC", "DAILY",
        "/TN", TASK_NAME,
        "/TR", f'"{python_path}" "{script_path}" --run-once',
        "/ST", f"{hour}:{minute}",
        "/F",  # 强制覆盖已有任务
    ]

    logger.info(f"注册Windows计划任务: {TASK_NAME}")
    logger.info(f"  命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logger.info(f"计划任务 '{TASK_NAME}' 注册成功！")
            logger.info(f"  每天 {hour}:{minute} 自动执行采集")
            return True
        else:
            logger.error(f"注册失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("注册命令超时")
        return False
    except FileNotFoundError:
        logger.error("未找到 schtasks.exe，请确认在Windows系统上运行")
        return False


def remove_windows_task():
    """删除 Windows 计划任务"""
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]

    logger.info(f"删除Windows计划任务: {TASK_NAME}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"计划任务 '{TASK_NAME}' 已删除")
            return True
        else:
            logger.warning(f"删除失败（任务可能不存在）: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"删除异常: {e}")
        return False


def check_task_exists() -> bool:
    """检查计划任务是否存在"""
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception:
        return False
