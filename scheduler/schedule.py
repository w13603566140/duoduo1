"""
定时任务调度器 - 基于APScheduler
支持每日定时采集 + 手动触发
"""
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import config
from utils.logger import logger

# 全局调度器实例
scheduler = BackgroundScheduler(
    timezone="Asia/Shanghai",
    job_defaults={"misfire_grace_time": 3600},  # 错过1小时内仍执行
)

# 记录手动触发的任务ID
_manual_jobs = set()
_lock = threading.Lock()


def _scrape_job_wrapper():
    """调度任务包装函数"""
    logger.info("=" * 60)
    logger.info("定时采集任务触发")
    logger.info("=" * 60)

    # 导入在这里避免循环依赖
    from core.scraper import run_scrape
    from core.db import get_session, create_scrape_log, finish_scrape_log

    log_id = None
    try:
        result = run_scrape()
        if result.get("success"):
            logger.info(f"定时采集完成: {result}")
        else:
            logger.error(f"定时采集失败: {result.get('error')}")
    except Exception as e:
        logger.error(f"定时采集异常: {e}", exc_info=True)


def start_scheduler():
    """启动后台调度器"""
    cron_parts = config.scrape_cron.split()
    if len(cron_parts) != 5:
        logger.error(f"无效的cron表达式: {config.scrape_cron}，使用默认值 0 2 * * *")
        cron_parts = ["0", "2", "*", "*", "*"]

    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
        timezone="Asia/Shanghai",
    )

    scheduler.add_job(
        _scrape_job_wrapper,
        trigger=trigger,
        id="daily_scrape",
        name="每日拼多多采集",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"定时任务已启动: {config.scrape_cron} (北京时间)")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")


def trigger_manual_scrape() -> int:
    """
    手动触发一次采集（在后台线程执行）。
    返回唯一的 job_id 供轮询状态。
    """
    job_id = f"manual_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    def _manual_job():
        try:
            _scrape_job_wrapper()
        finally:
            with _lock:
                _manual_jobs.discard(job_id)

    with _lock:
        _manual_jobs.add(job_id)

    # 直接在新线程中执行，不阻塞
    thread = threading.Thread(target=_manual_job, daemon=True)
    thread.start()

    logger.info(f"手动采集已触发: job_id={job_id}")
    return job_id  # 返回ID供前端轮询（实际用scrape_logs表查询状态）


def is_scraping() -> bool:
    """检查是否有正在执行的采集任务"""
    return len(_manual_jobs) > 0
