"""
数据库层 - SQLAlchemy 引擎、会话管理、CRUD 操作
"""
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from config import config
from utils.logger import logger

# SQLAlchemy Base
Base = declarative_base()

# 全局引擎和会话工厂
_engine = None
_SessionFactory = None


def get_engine():
    """获取或创建数据库引擎"""
    global _engine
    if _engine is None:
        # 确保 data 目录存在（SQLite 回退时用）
        db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(db_dir, exist_ok=True)

        url = config.database_url
        db_type = "MySQL" if config.use_mysql else "SQLite"
        logger.info(f"初始化数据库引擎: {db_type}")

        if config.use_mysql:
            _engine = create_engine(
                url,
                pool_size=5,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=False,
            )
        else:
            _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})

    return _engine


def get_session_factory() -> sessionmaker:
    """获取会话工厂"""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


def init_db():
    """初始化数据库，创建所有表"""
    engine = get_engine()
    # 导入所有模型以注册到Base.metadata
    import models.product  # noqa: F401
    import models.sales_record  # noqa: F401
    import models.scrape_log  # noqa: F401

    Base.metadata.create_all(engine)
    logger.info("数据库表初始化完成")


@contextmanager
def get_session() -> Session:
    """获取数据库会话（上下文管理器）"""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ========== 商品CRUD ==========

def upsert_product(session: Session, data: dict) -> "models.product.Product":
    """
    插入或更新商品记录。以 product_name 为主匹配字段。
    返回 Product 实例。
    """
    from models.product import Product

    name = data.get("name", "")[:512]
    shop_name = data.get("shop_name", "")[:256]
    keyword = data.get("keyword", "莜面鱼鱼")
    product_link = data.get("product_link", "")[:1024]

    # 按商品名前80字符匹配已有记录
    name_key = name[:80]
    existing = (
        session.query(Product)
        .filter(Product.product_name.like(name_key + '%'))
        .first()
    )

    if existing:
        existing.last_seen = datetime.now()
        existing.is_active = True
        existing.keyword = keyword
        if product_link:
            existing.product_link = product_link
        session.flush()
        return existing
    else:
        product = Product(
            product_name=name,
            shop_name=shop_name,
            keyword=keyword,
            product_link=product_link,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            is_active=True,
        )
        session.add(product)
        session.flush()
        return product


def compute_daily_sales(session: Session, product_id: int, current_volume: int) -> Optional[int]:
    """
    根据上一次采集的累计销量计算日销量差值。
    如果是第一次采集该商品，返回 None。
    """
    from models.sales_record import SalesRecord

    last_record = (
        session.query(SalesRecord)
        .filter(SalesRecord.product_id == product_id)
        .order_by(SalesRecord.scrape_time.desc())
        .first()
    )

    if last_record and last_record.sales_volume > 0:
        delta = current_volume - last_record.sales_volume
        # 异常检测：日增量超过累计销量的10倍，说明卡片关联错误
        if last_record.sales_volume > 0 and delta > last_record.sales_volume * 10:
            return None  # 当作首次采集，不记录异常日增量
        return max(0, delta)
    return None


def save_sales_record(session: Session, product_id: int, data: dict, daily_sales: Optional[int]):
    """保存一条销量快照"""
    from models.sales_record import SalesRecord

    record = SalesRecord(
        product_id=product_id,
        scrape_time=datetime.now(),
        scrape_date=date.today(),
        price=data.get("price"),
        sales_volume=data.get("sales_volume", 0),
        daily_sales=daily_sales,
        rank_position=data.get("rank_position"),
        raw_sales_text=data.get("raw_sales_text", "")[:64],
    )
    session.add(record)


# ========== 采集日志CRUD ==========

def create_scrape_log(session: Session, keyword: str = "") -> "models.scrape_log.ScrapeLog":
    """创建一条新的采集日志（状态=running）"""
    from models.scrape_log import ScrapeLog

    log_entry = ScrapeLog(
        started_at=datetime.now(),
        status="running",
        keyword_used=keyword,
    )
    session.add(log_entry)
    session.flush()
    return log_entry


def finish_scrape_log(
    session: Session,
    log_id: int,
    status: str,
    products_found: int = 0,
    records_saved: int = 0,
    error_message: str = None,
):
    """更新采集日志为完成/失败状态"""
    from models.scrape_log import ScrapeLog

    log_entry = session.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
    if log_entry:
        log_entry.status = status
        log_entry.finished_at = datetime.now()
        log_entry.products_found = products_found
        log_entry.records_saved = records_saved
        log_entry.error_message = error_message


# ========== 查询API（供Web使用） ==========

def get_dashboard_stats(session: Session) -> dict:
    """获取看板统计卡片数据"""
    from models.product import Product
    from models.sales_record import SalesRecord
    from models.scrape_log import ScrapeLog

    total_products = session.query(func.count(Product.id)).filter(Product.is_active == True).scalar()

    today = date.today()
    today_records = (
        session.query(func.count(SalesRecord.id))
        .filter(SalesRecord.scrape_date == today)
        .scalar()
    )

    today_avg_price = (
        session.query(func.avg(SalesRecord.price))
        .filter(SalesRecord.scrape_date == today, SalesRecord.price > 0)
        .scalar()
    )

    latest_scrape = (
        session.query(ScrapeLog.finished_at)
        .filter(ScrapeLog.status == "success")
        .order_by(ScrapeLog.finished_at.desc())
        .first()
    )

    return {
        "total_products": total_products or 0,
        "today_records": today_records or 0,
        "today_avg_price": round(float(today_avg_price), 2) if today_avg_price else None,
        "latest_scrape": latest_scrape[0].strftime("%Y-%m-%d %H:%M:%S") if latest_scrape and latest_scrape[0] else None,
        "latest_scrape_raw": latest_scrape[0] if latest_scrape else None,
    }


def get_ranking(session: Session, target_date: date = None, limit: int = 20) -> list:
    """获取指定日期销量排行（按日增量排序，去重每个商品最新记录）"""
    from models.sales_record import SalesRecord
    from models.product import Product

    if target_date is None:
        target_date = date.today()

    # 子查询：每个商品当天最新的一条记录
    from sqlalchemy import and_
    subq = (
        session.query(
            SalesRecord.product_id,
            func.max(SalesRecord.scrape_time).label('max_time')
        )
        .filter(SalesRecord.scrape_date == target_date)
        .group_by(SalesRecord.product_id)
        .subquery()
    )

    records = (
        session.query(SalesRecord, Product.product_name, Product.shop_name)
        .join(Product, SalesRecord.product_id == Product.id)
        .join(subq, and_(
            SalesRecord.product_id == subq.c.product_id,
            SalesRecord.scrape_time == subq.c.max_time
        ))
        .order_by(func.coalesce(SalesRecord.daily_sales, 0).desc())
        .limit(limit)
        .all()
    )

    result = []
    for rec, name, shop in records:
        result.append({
            "product_id": rec.product_id,
            "product_name": name,
            "shop_name": shop,
            "price": rec.price,
            "sales_volume": rec.sales_volume,
            "daily_sales": rec.daily_sales,
            "rank_position": rec.rank_position,
            "raw_sales_text": rec.raw_sales_text,
            "scrape_time": rec.scrape_time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return result


def get_trend(session: Session, product_id: int = None, days: int = 30) -> list:
    """获取销量趋势数据（可按商品筛选）"""
    from models.sales_record import SalesRecord
    from models.product import Product

    cutoff = date.today()
    # 简单日期计算
    from datetime import timedelta
    start_date = cutoff - timedelta(days=days)

    query = (
        session.query(SalesRecord, Product.product_name)
        .join(Product, SalesRecord.product_id == Product.id)
        .filter(SalesRecord.scrape_date >= start_date)
    )

    if product_id:
        query = query.filter(SalesRecord.product_id == product_id)

    records = query.order_by(SalesRecord.scrape_date.asc(), SalesRecord.product_id).all()

    result = []
    for rec, name in records:
        result.append({
            "product_id": rec.product_id,
            "product_name": name,
            "date": rec.scrape_date.isoformat() if rec.scrape_date else None,
            "sales_volume": rec.sales_volume,
            "daily_sales": rec.daily_sales,
            "price": rec.price,
        })
    return result


def get_products_list(session: Session, keyword: str = None, page: int = 1, per_page: int = 20) -> dict:
    """分页获取商品列表，含今日/昨日/周/月销量统计"""
    from models.product import Product
    from models.sales_record import SalesRecord
    from datetime import date, timedelta

    query = session.query(Product).filter(Product.is_active == True)

    if keyword:
        query = query.filter(Product.product_name.contains(keyword))

    total = query.count()
    products = query.order_by(Product.last_seen.desc()).offset((page - 1) * per_page).limit(per_page).all()

    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)

    items = []
    for p in products:
        # 获取最新销量
        latest_sales = (
            session.query(SalesRecord)
            .filter(SalesRecord.product_id == p.id)
            .order_by(SalesRecord.scrape_time.desc())
            .first()
        )

        # 今日销量（今天最新记录的 daily_sales）
        today_record = (
            session.query(SalesRecord)
            .filter(SalesRecord.product_id == p.id, SalesRecord.scrape_date == today)
            .order_by(SalesRecord.scrape_time.desc())
            .first()
        )

        # 昨日销量
        yesterday_record = (
            session.query(SalesRecord)
            .filter(SalesRecord.product_id == p.id, SalesRecord.scrape_date == yesterday)
            .order_by(SalesRecord.scrape_time.desc())
            .first()
        )

        # 近7天销量合计
        week_total = (
            session.query(func.coalesce(func.sum(SalesRecord.daily_sales), 0))
            .filter(SalesRecord.product_id == p.id, SalesRecord.scrape_date >= week_start)
            .scalar()
        )

        # 近30天销量合计
        month_total = (
            session.query(func.coalesce(func.sum(SalesRecord.daily_sales), 0))
            .filter(SalesRecord.product_id == p.id, SalesRecord.scrape_date >= month_start)
            .scalar()
        )

        items.append({
            "id": p.id,
            "product_name": p.product_name,
            "product_link": p.product_link or '',
            "shop_name": p.shop_name or '',
            "keyword": p.keyword,
            "first_seen": p.first_seen.strftime("%Y-%m-%d") if p.first_seen else None,
            "last_seen": p.last_seen.strftime("%Y-%m-%d %H:%M:%S") if p.last_seen else None,
            "latest_sales_volume": latest_sales.sales_volume if latest_sales else 0,
            "latest_price": latest_sales.price if latest_sales else None,
            "latest_daily_sales": latest_sales.daily_sales if latest_sales else None,
            # 新增字段
            "today_sales": today_record.daily_sales if today_record and today_record.daily_sales else 0,
            "yesterday_sales": yesterday_record.daily_sales if yesterday_record and yesterday_record.daily_sales else 0,
            "week_sales": int(week_total or 0),
            "month_sales": int(month_total or 0),
            "today_sales_volume": today_record.sales_volume if today_record else 0,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


def get_product_history(session: Session, product_id: int, days: int = 30) -> list:
    """获取单个商品的历史销量记录"""
    from models.sales_record import SalesRecord
    from datetime import timedelta

    start_date = date.today() - timedelta(days=days)

    records = (
        session.query(SalesRecord)
        .filter(SalesRecord.product_id == product_id, SalesRecord.scrape_date >= start_date)
        .order_by(SalesRecord.scrape_date.asc())
        .all()
    )

    return [
        {
            "scrape_date": r.scrape_date.isoformat() if r.scrape_date else None,
            "scrape_time": r.scrape_time.strftime("%Y-%m-%d %H:%M:%S") if r.scrape_time else None,
            "price": r.price,
            "sales_volume": r.sales_volume,
            "daily_sales": r.daily_sales,
            "rank_position": r.rank_position,
            "raw_sales_text": r.raw_sales_text,
        }
        for r in records
    ]


def get_scrape_logs(session: Session, page: int = 1, per_page: int = 20) -> dict:
    """分页获取采集日志"""
    from models.scrape_log import ScrapeLog

    total = session.query(func.count(ScrapeLog.id)).scalar()
    logs = (
        session.query(ScrapeLog)
        .order_by(ScrapeLog.started_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for log_entry in logs:
        duration = None
        if log_entry.finished_at and log_entry.started_at:
            duration = int((log_entry.finished_at - log_entry.started_at).total_seconds())

        items.append({
            "id": log_entry.id,
            "started_at": log_entry.started_at.strftime("%Y-%m-%d %H:%M:%S") if log_entry.started_at else None,
            "finished_at": log_entry.finished_at.strftime("%Y-%m-%d %H:%M:%S") if log_entry.finished_at else None,
            "status": log_entry.status or "unknown",
            "products_found": log_entry.products_found,
            "records_saved": log_entry.records_saved,
            "error_message": log_entry.error_message,
            "keyword_used": log_entry.keyword_used,
            "duration_seconds": duration,
        })

    return {
        "items": items,
        "total": total or 0,
        "page": page,
        "per_page": per_page,
        "pages": max(1, ((total or 0) + per_page - 1) // per_page),
    }
