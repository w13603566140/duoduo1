"""
全功能测试脚本 - 不依赖安卓设备，测试所有非设备相关功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from config import config


def separator(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_config():
    """1. 测试配置模块"""
    separator("1. 配置模块测试")
    assert config.search_keyword == "莜面鱼鱼", f"关键词错误: {config.search_keyword}"
    assert config.max_scrolls == 20
    assert config.web_port == 5000
    assert config.pdd_package == "com.xunmeng.pinduoduo"
    print(f"  [PASS] 搜索关键词: {config.search_keyword}")
    print(f"  [PASS] 数据库URL: {config.database_url}")
    print(f"  [PASS] 定时cron: {config.scrape_cron}")
    print(f"  [PASS] Web端口: {config.web_port}")


def test_parser():
    """2. 测试解析器"""
    separator("2. 解析器测试")
    from core.parser import parse_sales_volume, parse_price, normalize_product_name, normalize_shop_name

    # 销量解析
    cases = [
        ("已拼23件", 23),
        ("已拼10万件", 100000),
        ("已拼1.2万件", 12000),
        ("已拼10万+件", 100000),
        ("", 0),
        (None, 0),
    ]
    for text, expected in cases:
        result = parse_sales_volume(text)
        assert result == expected, f"销量解析失败: {text!r} -> {result} != {expected}"
    print("  [PASS] 销量解析: 6/6 通过")

    # 价格解析
    price_cases = [
        ("19.9", 19.9),
        ("1,299.00", 1299.0),
        ("", None),
        (None, None),
    ]
    for text, expected in price_cases:
        result = parse_price(text)
        if expected is None:
            assert result is None, f"价格应为None: {text!r}"
        else:
            assert abs(result - expected) < 0.01, f"价格解析失败: {text!r}"
    print("  [PASS] 价格解析: 4/4 通过")

    # 文本清洗
    assert normalize_product_name("  测试  ") == "测试"
    assert normalize_product_name("") == ""
    assert normalize_product_name(None) == ""
    assert len(normalize_product_name("x" * 600)) <= 512
    print("  [PASS] 商品名清洗: 通过")

    assert normalize_shop_name("  店铺  ") == "店铺"
    print("  [PASS] 店铺名清洗: 通过")


def test_db_init_and_models():
    """3. 测试数据库初始化和模型"""
    separator("3. 数据库与模型测试")
    from core.db import init_db, get_session, Base
    from models import Product, SalesRecord, ScrapeLog

    # 清理旧测试数据
    init_db()

    with get_session() as session:
        # 插入测试商品
        p1 = Product(product_name="莜面鱼鱼 正宗山西特产", shop_name="山西特产店", keyword="莜面鱼鱼")
        p2 = Product(product_name="莜面鱼鱼 手工制作500g", shop_name="五谷杂粮铺", keyword="莜面鱼鱼")
        session.add_all([p1, p2])
        session.flush()

        assert p1.id is not None
        assert p2.id is not None
        print(f"  [PASS] 商品创建: id={p1.id}, id={p2.id}")

        # 插入销量记录
        r1 = SalesRecord(
            product_id=p1.id, scrape_date=date.today(),
            price=19.9, sales_volume=23000, daily_sales=1200,
            rank_position=1, raw_sales_text="已拼2.3万件"
        )
        r2 = SalesRecord(
            product_id=p2.id, scrape_date=date.today(),
            price=25.0, sales_volume=15000, daily_sales=800,
            rank_position=2, raw_sales_text="已拼1.5万件"
        )
        r3 = SalesRecord(
            product_id=p1.id,
            scrape_date=date(2026, 7, 3),
            price=19.9, sales_volume=21800, daily_sales=1000,
            rank_position=1, raw_sales_text="已拼2.18万件"
        )
        session.add_all([r1, r2, r3])
        session.flush()
        print(f"  [PASS] 销量记录创建: 3条记录")

        # 插入采集日志
        from models.scrape_log import ScrapeLog
        log1 = ScrapeLog(status="success", started_at=datetime.now(),
                          finished_at=datetime.now(), products_found=10, records_saved=10,
                          keyword_used="莜面鱼鱼")
        log2 = ScrapeLog(status="failed", started_at=datetime.now(),
                          finished_at=datetime.now(), products_found=0, records_saved=0,
                          error_message="测试错误", keyword_used="莜面鱼鱼")
        session.add_all([log1, log2])
        print(f"  [PASS] 采集日志创建: 2条记录")

    print("  [OK] 数据库测试全部通过")


def test_db_queries():
    """4. 测试数据库查询函数"""
    separator("4. 数据库查询测试")
    from core.db import (get_session, get_dashboard_stats, get_ranking,
                          get_trend, get_products_list, get_product_history,
                          get_scrape_logs, upsert_product, compute_daily_sales,
                          save_sales_record)

    with get_session() as session:
        # 看板统计
        stats = get_dashboard_stats(session)
        assert stats["total_products"] >= 2
        assert stats["today_records"] >= 2
        print(f"  [PASS] 看板统计: 商品={stats['total_products']}, "
              f"今日记录={stats['today_records']}, 均价={stats['today_avg_price']}")

        # 排行
        ranking = get_ranking(session, limit=10)
        assert len(ranking) >= 2
        assert ranking[0]["sales_volume"] >= ranking[1]["sales_volume"]
        print(f"  [PASS] 销量排行: {len(ranking)}条, TOP1销量={ranking[0]['sales_volume']}")

        # 趋势
        trend = get_trend(session, days=30)
        assert len(trend) >= 2
        print(f"  [PASS] 趋势数据: {len(trend)}条")

        # 商品列表
        products = get_products_list(session, page=1, per_page=10)
        assert products["total"] >= 2
        print(f"  [PASS] 商品列表: 共{products['total']}个, 当前页{len(products['items'])}个")

        # 关键词搜索
        products_filtered = get_products_list(session, keyword="正宗", page=1)
        assert products_filtered["total"] >= 1
        print(f"  [PASS] 商品搜索('正宗'): 找到{products_filtered['total']}个")

        # 商品历史
        from models.product import Product
        p1 = session.query(Product).filter(Product.product_name.contains("正宗")).first()
        history = get_product_history(session, p1.id, days=30)
        assert len(history) >= 1
        print(f"  [PASS] 商品历史: id={p1.id}, {len(history)}条记录")

        # 采集日志
        logs = get_scrape_logs(session, page=1)
        assert logs["total"] >= 2
        print(f"  [PASS] 采集日志: 共{logs['total']}条")

    print("  [OK] 查询测试全部通过")


def test_crud_operations():
    """5. 测试CRUD增删改操作"""
    separator("5. CRUD操作测试")
    from core.db import (get_session, upsert_product, compute_daily_sales,
                          save_sales_record, create_scrape_log, finish_scrape_log)

    with get_session() as session:
        # upsert: 新商品
        data = {"name": "莜面鱼鱼 测试新品", "shop_name": "测试店铺", "keyword": "莜面鱼鱼"}
        product = upsert_product(session, data)
        assert product.id is not None
        print(f"  [PASS] upsert 新建: id={product.id}, name={product.product_name[:30]}")

        # upsert: 同名商品应更新而非新建
        data2 = {"name": "莜面鱼鱼 测试新品", "shop_name": "测试店铺", "keyword": "莜面鱼鱼"}
        product2 = upsert_product(session, data2)
        assert product2.id == product.id
        print(f"  [PASS] upsert 更新: same id={product2.id} (no duplicate)")

        # 计算日销量
        daily = compute_daily_sales(session, product.id, 500)
        assert daily is None  # 首次采集，无历史
        print(f"  [PASS] 日销量计算(首次): daily=None")

        # 保存记录
        save_sales_record(session, product.id,
                          {"price": 19.9, "sales_volume": 500, "rank_position": 5,
                           "raw_sales_text": "已拼500件"},
                          daily_sales=None)
        print(f"  [PASS] 销量记录保存: vol=500")

        # 第二次采集
        daily2 = compute_daily_sales(session, product.id, 620)
        assert daily2 == 120
        print(f"  [PASS] 日销量计算(第二次): daily=120 (620-500)")

        save_sales_record(session, product.id,
                          {"price": 19.5, "sales_volume": 620, "rank_position": 4,
                           "raw_sales_text": "已拼620件"},
                          daily_sales=120)
        print(f"  [PASS] 第二次记录保存: vol=620, daily=120")

        # 采集日志
        log_entry = create_scrape_log(session, "莜面鱼鱼")
        assert log_entry.status == "running"
        print(f"  [PASS] 采集日志创建: id={log_entry.id}, status=running")

        finish_scrape_log(session, log_entry.id, "success",
                          products_found=15, records_saved=15)
        # 需要重新查询验证
        from models.scrape_log import ScrapeLog
        updated = session.query(ScrapeLog).filter(ScrapeLog.id == log_entry.id).first()
        assert updated.status == "success"
        assert updated.products_found == 15
        print(f"  [PASS] 日志更新: status=success, products=15")

    print("  [OK] CRUD测试全部通过")


def test_utils():
    """6. 测试工具模块"""
    separator("6. 工具模块测试")
    from utils.helpers import retry, normalize_text, today_str, now_str
    from utils.logger import logger

    assert today_str() == date.today().isoformat()
    print(f"  [PASS] today_str: {today_str()}")

    now = now_str()
    assert len(now) == 19  # YYYY-MM-DD HH:MM:SS
    print(f"  [PASS] now_str: {now}")

    assert normalize_text("  a  b  ") == "a b"
    assert normalize_text("") == ""
    long_text = "x" * 600
    assert len(normalize_text(long_text)) <= 512
    print(f"  [PASS] normalize_text: 通过")

    # 重试装饰器测试
    call_count = [0]

    @retry(max_attempts=3, delay=0.1)
    def flaky_func():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError("flaky error")
        return "success"

    result = flaky_func()
    assert result == "success"
    assert call_count[0] == 3
    print(f"  [PASS] retry装饰器: 重试{call_count[0]}次后成功")

    # 始终失败的函数
    call_count2 = [0]

    @retry(max_attempts=3, delay=0.1)
    def always_fail():
        call_count2[0] += 1
        raise RuntimeError("always fail")

    try:
        always_fail()
        assert False, "Should have raised"
    except RuntimeError:
        assert call_count2[0] == 3
    print(f"  [PASS] retry装饰器: 重试{call_count2[0]}次后抛出异常")

    print("  [OK] 工具模块测试全部通过")


def test_web_app():
    """7. 测试Flask Web应用"""
    separator("7. Web应用测试")
    from web.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # 页面路由
    routes_to_test = ["/", "/products", "/logs"]
    for route in routes_to_test:
        resp = client.get(route)
        assert resp.status_code == 200, f"{route} 返回 {resp.status_code}"
        assert b"PDD" in resp.data or len(resp.data) > 0
    print(f"  [PASS] 页面路由: 3/3 返回200")

    # API端点
    api_endpoints = [
        "/api/dashboard/stats",
        "/api/dashboard/ranking?limit=5",
        "/api/dashboard/trend?days=7",
        "/api/products?page=1&per_page=10",
        "/api/logs?page=1",
    ]
    for ep in api_endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200, f"{ep} 返回 {resp.status_code}"
        data = resp.get_json()
        assert data is not None, f"{ep} 返回非JSON"
    print(f"  [PASS] API端点: {len(api_endpoints)}/5 返回200 JSON")

    # 统计API数据验证
    resp = client.get("/api/dashboard/stats")
    stats = resp.get_json()
    assert stats["total_products"] >= 3
    print(f"  [PASS] API数据一致性: total_products={stats['total_products']}, "
          f"today_records={stats['today_records']}")

    # 商品详情API
    from models.product import Product
    from core.db import get_session
    with get_session() as session:
        p = session.query(Product).first()
        pid = p.id

    resp = client.get(f"/api/products/{pid}/info")
    assert resp.status_code == 200
    info = resp.get_json()
    assert info["product_name"] is not None
    print(f"  [PASS] 商品详情API: {info['product_name'][:30]}...")

    resp = client.get(f"/api/products/{pid}/history?days=7")
    assert resp.status_code == 200
    history = resp.get_json()
    assert len(history) >= 1
    print(f"  [PASS] 商品历史API: {len(history)}条")

    # 手动采集触发API（无设备时返回busy或正常）
    resp = client.post("/api/scrape/trigger")
    data = resp.get_json()
    # 可能返回 busy (有任务在跑) 或 started
    assert resp.status_code in (200, 409)
    print(f"  [PASS] 采集触发API: status={resp.status_code}, {data.get('message', '')}")

    # 采集状态API
    resp = client.get("/api/scrape/status")
    assert resp.status_code == 200
    print(f"  [PASS] 采集状态API: {resp.get_json()}")

    # 商品搜索
    resp = client.get("/api/products?keyword=正宗")
    assert resp.status_code == 200
    search_result = resp.get_json()
    assert search_result["total"] >= 1
    print(f"  [PASS] 商品搜索API: keyword=正宗, found={search_result['total']}")

    print("  [OK] Web应用测试全部通过")


def test_scheduler():
    """8. 测试调度器模块"""
    separator("8. 调度器模块测试")
    from scheduler.schedule import trigger_manual_scrape, is_scraping

    # 检查没有采集任务在运行（没有设备所以实际不会真的运行）
    scraping = is_scraping()
    print(f"  [PASS] 采集状态检查: is_scraping={scraping}")

    # 触发手动采集（会在后台线程运行，无设备时会失败但不影响测试）
    job_id = trigger_manual_scrape()
    assert job_id is not None
    print(f"  [PASS] 手动采集触发: job_id={job_id}")

    # Windows任务计划程序（仅测试导入和函数签名）
    from scheduler.windows_task import register_windows_task, remove_windows_task, check_task_exists
    import inspect
    assert callable(register_windows_task)
    assert callable(remove_windows_task)
    assert callable(check_task_exists)
    print(f"  [PASS] Windows任务模块: 函数导入正常")

    print("  [OK] 调度器测试全部通过")


def test_edge_cases():
    """9. 边界情况测试"""
    separator("9. 边界情况测试")
    from core.parser import parse_sales_volume, parse_price
    from utils.helpers import normalize_text

    # 极端销量文本
    edge_cases = [
        ("已拼0件", 0),
        ("已拼99999999件", 99999999),
        ("已拼0.1万件", 1000),
        ("已拼0.01万件", 100),
        ("已拼1,234.56万件", 12345600),
    ]
    for text, expected in edge_cases:
        result = parse_sales_volume(text)
        assert result == expected, f"Edge case failed: {text!r} -> {result} != {expected}"
    print(f"  [PASS] 销量极端值: {len(edge_cases)}/5 通过")

    # Unicode文本处理
    unicode_text = "莜面鱼鱼 热销"
    cleaned = normalize_text(unicode_text)
    assert "莜面鱼鱼" in cleaned
    print(f"  [PASS] Unicode文本: '{cleaned}'")

    # 空值处理
    assert parse_sales_volume(None) == 0
    assert parse_sales_volume("") == 0
    assert parse_price(None) is None
    assert parse_price("") is None
    assert normalize_text(None) == ""
    print(f"  [PASS] 空值处理: 全部正确")

    print("  [OK] 边界情况测试全部通过")


def test_data_integrity():
    """10. 数据完整性测试"""
    separator("10. 数据完整性测试")
    from core.db import get_session
    from models.product import Product
    from models.sales_record import SalesRecord
    from sqlalchemy import func

    with get_session() as session:
        # 验证没有孤儿记录
        product_count = session.query(func.count(Product.id)).scalar()
        record_count = session.query(func.count(SalesRecord.id)).scalar()

        orphan_count = (
            session.query(func.count(SalesRecord.id))
            .select_from(SalesRecord)
            .outerjoin(Product, SalesRecord.product_id == Product.id)
            .filter(Product.id == None)
            .scalar()
        )
        assert orphan_count == 0, f"发现{orphan_count}条孤儿销量记录"
        print(f"  [PASS] 无孤儿记录: products={product_count}, records={record_count}")

        # 验证daily_sales值合理（应为正数或None）
        negative_daily = (
            session.query(func.count(SalesRecord.id))
            .filter(SalesRecord.daily_sales != None, SalesRecord.daily_sales < 0)
            .scalar()
        )
        assert negative_daily == 0, f"发现{negative_daily}条负日销量"
        print(f"  [PASS] 日销量数据合法: 无负值")

        # 验证scrape_date不为空
        null_date = (
            session.query(func.count(SalesRecord.id))
            .filter(SalesRecord.scrape_date == None)
            .scalar()
        )
        assert null_date == 0
        print(f"  [PASS] 采集日期完整: 无空值")

    print("  [OK] 数据完整性测试全部通过")


if __name__ == "__main__":
    print()
    print("*" * 60)
    print("  拼多多销量采集监控系统 - 全功能测试")
    print("*" * 60)

    results = []
    tests = [
        ("配置模块", test_config),
        ("解析器", test_parser),
        ("数据库与模型", test_db_init_and_models),
        ("数据库查询", test_db_queries),
        ("CRUD操作", test_crud_operations),
        ("工具模块", test_utils),
        ("Web应用", test_web_app),
        ("调度器", test_scheduler),
        ("边界情况", test_edge_cases),
        ("数据完整性", test_data_integrity),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            results.append((name, "PASS"))
            passed += 1
        except Exception as e:
            results.append((name, f"FAIL: {e}"))
            failed += 1
            import traceback
            traceback.print_exc()

    # 汇总报告
    separator("测试汇总")
    print(f"  {'模块':<20} {'结果'}")
    print(f"  {'-' * 40}")
    for name, result in results:
        status = "[OK]" if result == "PASS" else "[FAIL]"
        print(f"  {name:<20} {status} {result if result != 'PASS' else ''}")

    print()
    print(f"  通过: {passed}/{len(tests)}  失败: {failed}/{len(tests)}")

    if failed == 0:
        print()
        print("  *** 全部测试通过! ***")
        sys.exit(0)
    else:
        print()
        print(f"  *** {failed} 项测试失败 ***")
        sys.exit(1)
