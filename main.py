#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拼多多商品销量采集监控系统 - 主入口

用法:
    python main.py                # 启动Web看板（默认模式，含定时任务）
    python main.py --web          # 仅启动Web看板
    python main.py --run-once     # 执行一次采集后退出
    python main.py --register-task  # 注册Windows计划任务
    python main.py --remove-task    # 删除Windows计划任务
"""
import argparse
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from utils.logger import logger, setup_logger


def run_single_scrape():
    """执行一次采集并打印结果"""
    logger.info("=" * 60)
    logger.info("模式: 单次采集")
    logger.info(f"关键词: {config.search_keyword}")
    logger.info("=" * 60)

    from core.db import init_db
    init_db()

    from core.scraper import run_scrape
    result = run_scrape()

    if result.get("success"):
        logger.info(f"✅ 采集成功！")
        logger.info(f"   发现商品: {result.get('products_found', 0)}")
        logger.info(f"   保存记录: {result.get('records_saved', 0)}")
    else:
        logger.error(f"❌ 采集失败: {result.get('error', '未知错误')}")

    return result


def start_web_dashboard():
    """启动Web看板（含后台定时任务）"""
    logger.info("=" * 60)
    logger.info("模式: Web看板 + 定时任务")
    logger.info(f"访问地址: http://localhost:{config.web_port}")
    logger.info(f"定时任务: {config.scrape_cron} (北京时间)")
    logger.info("=" * 60)

    # 初始化数据库
    from core.db import init_db
    init_db()

    # 启动定时调度器
    from scheduler.schedule import start_scheduler, stop_scheduler
    start_scheduler()

    # 启动Flask
    from web.app import create_app
    app = create_app()

    try:
        app.run(
            host=config.web_host,
            port=config.web_port,
            debug=config.web_debug,
            use_reloader=False,  # 避免APScheduler重复启动
        )
    finally:
        stop_scheduler()


def main():
    parser = argparse.ArgumentParser(
        description="拼多多商品销量采集监控系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                  # 启动Web看板
  python main.py --run-once       # 执行一次采集
  python main.py --register-task  # 注册Windows定时任务
  python main.py --remove-task    # 删除Windows定时任务
        """,
    )

    parser.add_argument(
        "--run-once",
        action="store_true",
        help="执行一次采集后退出",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="启动Web看板（不含定时任务）",
    )
    parser.add_argument(
        "--no-scheduler",
        action="store_true",
        help="启动Web看板但不启动定时任务",
    )
    parser.add_argument(
        "--register-task",
        action="store_true",
        help="注册Windows计划任务（每天定时执行）",
    )
    parser.add_argument(
        "--remove-task",
        action="store_true",
        help="删除Windows计划任务",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help=f"搜索关键词（默认: {config.search_keyword}）",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="设备序列号（默认自动检测）",
    )

    args = parser.parse_args()

    # 处理命令
    if args.register_task:
        from scheduler.windows_task import register_windows_task
        register_windows_task()
        return

    if args.remove_task:
        from scheduler.windows_task import remove_windows_task
        remove_windows_task()
        return

    if args.run_once:
        # 覆盖关键词和设备
        if args.keyword:
            config.search_keyword = args.keyword
        if args.device:
            config.device_serial = args.device
        run_single_scrape()
        return

    # 默认：启动Web看板
    if args.no_scheduler:
        # 仅Web，无定时任务
        logger.info("模式: Web看板（无定时任务）")
        from core.db import init_db
        init_db()
        from web.app import create_app
        app = create_app()
        app.run(
            host=config.web_host,
            port=config.web_port,
            debug=config.web_debug,
        )
    else:
        start_web_dashboard()


if __name__ == "__main__":
    main()
