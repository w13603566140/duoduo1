"""
REST API 端点 - JSON 数据接口
"""
from datetime import date, datetime
from flask import Blueprint, jsonify, request

from core.db import (
    get_session,
    get_dashboard_stats,
    get_ranking,
    get_trend,
    get_products_list,
    get_product_history,
    get_scrape_logs,
)

api_bp = Blueprint("api", __name__)


@api_bp.route("/dashboard/stats")
def api_dashboard_stats():
    """看板统计卡片数据"""
    with get_session() as session:
        stats = get_dashboard_stats(session)
    return jsonify(stats)


@api_bp.route("/dashboard/ranking")
def api_ranking():
    """销量排行"""
    date_str = request.args.get("date")
    limit = request.args.get("limit", 20, type=int)

    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "日期格式应为 YYYY-MM-DD"}), 400

    with get_session() as session:
        ranking = get_ranking(session, target_date, limit)
    return jsonify(ranking)


@api_bp.route("/dashboard/trend")
def api_trend():
    """销量趋势数据"""
    product_id = request.args.get("product_id", type=int)
    days = request.args.get("days", 30, type=int)

    with get_session() as session:
        trend = get_trend(session, product_id, days)
    return jsonify(trend)


@api_bp.route("/products")
def api_products():
    """商品列表（分页）"""
    keyword = request.args.get("keyword")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    with get_session() as session:
        result = get_products_list(session, keyword, page, per_page)
    return jsonify(result)


@api_bp.route("/products/<int:product_id>/history")
def api_product_history(product_id: int):
    """单个商品历史销量"""
    days = request.args.get("days", 30, type=int)

    with get_session() as session:
        history = get_product_history(session, product_id, days)
    return jsonify(history)


@api_bp.route("/products/<int:product_id>/info")
def api_product_info(product_id: int):
    """单个商品基本信息"""
    from models.product import Product
    from models.sales_record import SalesRecord

    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return jsonify({"error": "商品不存在"}), 404

        latest_sales = (
            session.query(SalesRecord)
            .filter(SalesRecord.product_id == product_id)
            .order_by(SalesRecord.scrape_time.desc())
            .first()
        )

        return jsonify({
            "id": product.id,
            "product_name": product.product_name,
            "product_link": product.product_link or '',
            "shop_name": product.shop_name or '',
            "keyword": product.keyword,
            "first_seen": product.first_seen.strftime("%Y-%m-%d") if product.first_seen else None,
            "last_seen": product.last_seen.strftime("%Y-%m-%d %H:%M:%S") if product.last_seen else None,
            "is_active": product.is_active,
            "latest_sales_volume": latest_sales.sales_volume if latest_sales else 0,
            "latest_price": latest_sales.price if latest_sales else None,
            "latest_daily_sales": latest_sales.daily_sales if latest_sales else None,
            "latest_raw_sales_text": latest_sales.raw_sales_text if latest_sales else "",
        })


@api_bp.route("/logs")
def api_logs():
    """采集日志列表（分页）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    with get_session() as session:
        result = get_scrape_logs(session, page, per_page)
    return jsonify(result)


@api_bp.route("/scrape/trigger", methods=["POST"])
def api_trigger_scrape():
    """手动触发采集"""
    from scheduler.schedule import trigger_manual_scrape, is_scraping

    if is_scraping():
        return jsonify({"status": "busy", "message": "正在执行采集任务，请稍后再试"}), 409

    job_id = trigger_manual_scrape()
    return jsonify({
        "status": "started",
        "message": "采集任务已触发",
        "job_id": job_id,
    })


@api_bp.route("/scrape/status")
def api_scrape_status():
    """获取最新采集状态"""
    with get_session() as session:
        logs = get_scrape_logs(session, page=1, per_page=1)
        if logs["items"]:
            latest = logs["items"][0]
            return jsonify({
                "status": latest["status"],
                "products_found": latest["products_found"],
                "records_saved": latest["records_saved"],
                "started_at": latest["started_at"],
                "finished_at": latest["finished_at"],
                "duration": latest["duration_seconds"],
                "error": latest["error_message"],
            })

    return jsonify({"status": "never", "message": "暂无采集记录"})


@api_bp.route("/scheduler/status")
def api_scheduler_status():
    """获取调度器状态，如未运行则自动启动"""
    from scheduler.schedule import scheduler, start_scheduler

    was_running = scheduler.running
    if not was_running:
        try:
            start_scheduler()
        except Exception:
            pass

    job = scheduler.get_job("daily_scrape")
    return jsonify({
        "scheduler_running": scheduler.running,
        "auto_started": not was_running and scheduler.running,
        "job_exists": job is not None,
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "cron": str(job.trigger) if job else None,
    })


# ======== 系统设置 API ========

@api_bp.route("/settings")
def api_get_settings():
    """获取当前设置"""
    from config import config as cfg
    return jsonify({
        "keyword": cfg.search_keyword,
        "max_scrolls": cfg.max_scrolls,
        "scroll_pause": cfg.scroll_pause_seconds,
        "max_results": cfg.max_results,
        "cron": cfg.scrape_cron,
        "device_serial": cfg.device_serial,
        "web_port": cfg.web_port,
    })


@api_bp.route("/settings", methods=["POST"])
def api_save_settings():
    """保存设置"""
    import os
    from config import config as cfg

    data = request.get_json()
    if not data:
        return jsonify({"error": "无效数据"}), 400

    updates = {}

    if "keyword" in data and data["keyword"]:
        cfg.search_keyword = data["keyword"]
        updates["SEARCH_KEYWORD"] = data["keyword"]

    if "max_scrolls" in data:
        cfg.max_scrolls = int(data["max_scrolls"])
        updates["MAX_SCROLLS"] = str(data["max_scrolls"])

    if "scroll_pause" in data:
        cfg.scroll_pause_seconds = float(data["scroll_pause"])
        updates["SCROLL_PAUSE_SECONDS"] = str(data["scroll_pause"])

    if "max_results" in data:
        cfg.max_results = int(data["max_results"])
        updates["MAX_RESULTS"] = str(data["max_results"])

    if "cron" in data and data["cron"]:
        cfg.scrape_cron = data["cron"]
        updates["SCRAPE_CRON"] = data["cron"]
        # 重新调度
        _reschedule_job(data["cron"])

    if "device_serial" in data:
        cfg.device_serial = data["device_serial"] or ""
        updates["DEVICE_SERIAL"] = data["device_serial"] or ""

    # 写入 .env 文件持久化
    _save_env(updates)

    return jsonify({"status": "ok", "updates": list(updates.keys())})


def _save_env(updates: dict):
    """将更新写入.env文件"""
    import os
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

    # 读取现有配置
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    existing[key.strip()] = val.strip()

    # 合并更新
    existing.update(updates)

    # 写回
    with open(env_path, 'w', encoding='utf-8') as f:
        for key, val in existing.items():
            f.write('{}={}\n'.format(key, val))


def _reschedule_job(cron: str):
    """更新APScheduler定时任务，如调度器未启动则先启动"""
    from scheduler.schedule import scheduler, start_scheduler
    from apscheduler.triggers.cron import CronTrigger

    parts = cron.split()
    if len(parts) != 5:
        return

    # 确保调度器运行中
    if not scheduler.running:
        try:
            start_scheduler()
        except Exception:
            pass

    try:
        job = scheduler.get_job("daily_scrape")
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1],
            day=parts[2], month=parts[3],
            day_of_week=parts[4],
            timezone="Asia/Shanghai",
        )
        if job:
            job.reschedule(trigger=trigger)
    except Exception:
        pass
