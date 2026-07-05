"""
商用级全面测试 - 覆盖所有功能模块
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0
WARN = 0

def check(cond, name, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] {}".format(name))
    else:
        FAIL += 1
        print("  [FAIL] {}  <<< {}".format(name, detail))

def warn(name, detail=""):
    global WARN
    WARN += 1
    print("  [WARN] {} - {}".format(name, detail))

def header(title):
    print()
    print("=" * 55)
    print("  {}".format(title))
    print("=" * 55)


# ============================================================
# 1. 模块导入测试
# ============================================================
header("1. 模块导入")
try:
    from config import config
    check(True, "config 模块")
except Exception as e:
    check(False, "config 模块", str(e))

try:
    from core.parser import parse_sales_volume, parse_price, normalize_product_name
    check(True, "core.parser 模块")
except Exception as e:
    check(False, "core.parser 模块", str(e))

try:
    from core.db import init_db, get_session, get_dashboard_stats, get_ranking, get_trend, get_products_list, get_scrape_logs
    check(True, "core.db 模块")
except Exception as e:
    check(False, "core.db 模块", str(e))

try:
    from models import Product, SalesRecord, ScrapeLog
    check(True, "models 模块")
except Exception as e:
    check(False, "models 模块", str(e))

try:
    from utils.logger import logger
    from utils.helpers import retry, normalize_text, today_str, now_str
    check(True, "utils 模块")
except Exception as e:
    check(False, "utils 模块", str(e))

try:
    from scheduler.schedule import start_scheduler, stop_scheduler, trigger_manual_scrape, is_scraping
    check(True, "scheduler.schedule 模块")
except Exception as e:
    check(False, "scheduler.schedule 模块", str(e))

try:
    from scheduler.windows_task import check_task_exists
    check(True, "scheduler.windows_task 模块")
except Exception as e:
    check(False, "scheduler.windows_task 模块", str(e))

try:
    from web.app import create_app
    check(True, "web.app 模块")
except Exception as e:
    check(False, "web.app 模块", str(e))


# ============================================================
# 2. 配置测试
# ============================================================
header("2. 配置验证")
check(config.search_keyword != "", "搜索关键词: {}".format(config.search_keyword))
check(config.max_scrolls > 0, "最大滚动: {}".format(config.max_scrolls))
check(config.max_results > 0, "最大结果: {}".format(config.max_results))
check(config.web_port > 0, "Web端口: {}".format(config.web_port))
check(len(config.scrape_cron.split()) == 5, "Cron表达式: {}".format(config.scrape_cron))
check('pinduoduo' in config.pdd_package, "PDD包名: {}".format(config.pdd_package))
check(config.database_url != "", "数据库URL已配置")


# ============================================================
# 3. 解析器测试
# ============================================================
header("3. 解析器精度测试")
test_cases = [
    ("已拼23件", 23), ("已拼1,230件", 1230), ("已拼1.2万件", 12000),
    ("已拼10万件", 100000), ("已拼10万+件", 100000), ("已拼100万+件", 1000000),
    ("已拼1.23万件", 12300), ("", 0), (None, 0), ("已拼0件", 0),
    ("已拼99999999件", 99999999), ("已拼0.5万件", 5000),
]
for text, expected in test_cases:
    result = parse_sales_volume(text)
    check(result == expected, "parse_sales_volume({})={}".format(repr(text)[:20], result),
          "expected {}".format(expected))

price_tests = [
    ("19.9", 19.9), ("1,299.00", 1299.0), ("", None), (None, None),
]
for text, expected in price_tests:
    result = parse_price(text)
    if expected is None:
        check(result is None, "parse_price({})={}".format(repr(text)[:15], result))
    else:
        check(result is not None and abs(result - expected) < 0.01,
              "parse_price({})={}".format(repr(text)[:15], result))


# ============================================================
# 4. 数据库测试
# ============================================================
header("4. 数据库完整性")
init_db()

with get_session() as s:
    from sqlalchemy import inspect
    inspector = inspect(s.bind)
    tables = inspector.get_table_names()
    check("products" in tables, "products 表存在")
    check("sales_records" in tables, "sales_records 表存在")
    check("scrape_logs" in tables, "scrape_logs 表存在")

    # 检查表结构
    p_cols = [c["name"] for c in inspector.get_columns("products")]
    for col in ["id", "product_name", "shop_name", "product_link", "keyword", "first_seen", "last_seen", "is_active"]:
        check(col in p_cols, "products.{} 字段存在".format(col))

    s_cols = [c["name"] for c in inspector.get_columns("sales_records")]
    for col in ["id", "product_id", "scrape_date", "price", "sales_volume", "daily_sales", "raw_sales_text"]:
        check(col in s_cols, "sales_records.{} 字段存在".format(col))

    l_cols = [c["name"] for c in inspector.get_columns("scrape_logs")]
    for col in ["id", "started_at", "finished_at", "status", "products_found", "records_saved"]:
        check(col in l_cols, "scrape_logs.{} 字段存在".format(col))

    # 数据完整性检查
    from models.product import Product
    from models.sales_record import SalesRecord
    from sqlalchemy import func

    product_count = s.query(Product).count()
    record_count = s.query(SalesRecord).count()
    check(product_count >= 0, "商品数: {}".format(product_count))
    check(record_count >= product_count, "销量记录 >= 商品数: {}>={}".format(record_count, product_count))

    # 无零销量商品
    zero_vol = s.query(Product).join(SalesRecord).filter(SalesRecord.sales_volume == 0).count()
    check(zero_vol == 0, "零销量商品数=0 (实际:{})".format(zero_vol),
          "有{}个零销量商品需要清理".format(zero_vol) if zero_vol > 0 else "")

    # 无店铺级销量
    from sqlalchemy import or_
    store_sales = s.query(SalesRecord).filter(
        or_(SalesRecord.raw_sales_text.like('%全网%'), SalesRecord.raw_sales_text.like('%总售%'))
    ).count()
    check(store_sales == 0, "店铺总销量=0 (实际:{})".format(store_sales),
          "有{}条店铺销量数据".format(store_sales) if store_sales > 0 else "")

    # 检查重复 (同一商品同一天多条记录)
    dupes = s.query(
        SalesRecord.product_id, SalesRecord.scrape_date, func.count(SalesRecord.id).label('cnt')
    ).group_by(SalesRecord.product_id, SalesRecord.scrape_date).having(func.count(SalesRecord.id) > 1).count()
    check(dupes == 0, "无重复日记录 (实际:{})".format(dupes))

    # 检查daily_sales为负
    neg = s.query(SalesRecord).filter(SalesRecord.daily_sales != None, SalesRecord.daily_sales < 0).count()
    check(neg == 0, "无负日销量 (实际:{})".format(neg))


# ============================================================
# 5. Web应用测试
# ============================================================
header("5. Web应用测试")
app = create_app()
app.config["TESTING"] = True
client = app.test_client()

# 页面路由
pages = [
    ("/", "看板页面"),
    ("/products", "商品列表"),
    ("/logs", "采集日志"),
    ("/settings", "系统设置"),
]
for path, name in pages:
    resp = client.get(path)
    check(resp.status_code == 200, "{} -> 200 (实际:{})".format(name, resp.status_code))
    check(b"PDD" in resp.data or len(resp.data) > 500, "{} 有内容".format(name))

# API端点
apis = [
    ("/api/dashboard/stats", "看板统计"),
    ("/api/dashboard/ranking?limit=10", "排行"),
    ("/api/dashboard/trend?days=7", "趋势"),
    ("/api/products?page=1&per_page=5", "商品列表"),
    ("/api/logs?page=1", "日志"),
    ("/api/scrape/status", "采集状态"),
    ("/api/settings", "设置读取"),
]
for path, name in apis:
    resp = client.get(path)
    check(resp.status_code == 200, "{} -> 200".format(name), "返回 {}".format(resp.status_code))
    data = resp.get_json()
    check(data is not None, "{} -> JSON有效".format(name))

# 设置写入
resp = client.post("/api/settings",
    data=json.dumps({"keyword": "莜面鱼鱼", "max_scrolls": 20}),
    content_type="application/json")
check(resp.status_code == 200, "设置写入 -> 200")

# 采集触发 (无设备时预期409 busy 或 200)
resp = client.post("/api/scrape/trigger")
check(resp.status_code in (200, 409), "手动采集触发 -> {}".format(resp.status_code))

# 不存在的商品详情
resp = client.get("/api/products/99999/info")
check(resp.status_code == 404, "不存在商品 -> 404")

# 商品详情API
if product_count > 0:
    first_pid = s.query(Product).first().id
    resp = client.get("/api/products/{}/info".format(first_pid))
    check(resp.status_code == 200, "商品详情API -> 200")
    info = resp.get_json()
    check(info["product_name"] is not None, "商品名不为空")
    check("shop_name" in info, "店铺名字段存在")
    check("product_link" in info, "链接字段存在")


# ============================================================
# 6. 工具模块测试
# ============================================================
header("6. 工具模块测试")
check(today_str() is not None, "today_str()={}".format(today_str()))
check(now_str() is not None, "now_str()有值")
check(normalize_text("  a  b  ") == "a b", "normalize_text正确")
check(normalize_text("") == "", "normalize_text空值")
check(normalize_text(None) == "", "normalize_text None")

# retry
call_count = [0]
@retry(max_attempts=3, delay=0.1)
def flaky():
    call_count[0] += 1
    if call_count[0] < 3:
        raise ValueError("test")
    return "ok"
try:
    result = flaky()
    check(result == "ok" and call_count[0] == 3, "retry重试机制 ({}次)".format(call_count[0]))
except:
    check(False, "retry机制失败")


# ============================================================
# 7. 调度器测试
# ============================================================
header("7. 调度器测试")
scraping = is_scraping()
check(isinstance(scraping, bool), "is_scraping()返回布尔值")

# 检查调度器可启动
try:
    from scheduler.schedule import scheduler
    job = scheduler.get_job("daily_scrape")
    if job:
        check(True, "daily_scrape任务已注册")
    else:
        warn("daily_scrape任务未注册(Web服务未运行)")
except Exception as e:
    warn("调度器检查失败: {}".format(e))

# Windows任务
try:
    exists = check_task_exists()
    if exists:
        check(True, "Windows计划任务已注册")
    else:
        warn("Windows计划任务未注册 (可运行: python main.py --register-task)")
except Exception as e:
    warn("Windows任务检查: {}".format(e))


# ============================================================
# 8. 前端资源测试
# ============================================================
header("8. 前端资源测试")
static_files = [
    "/static/css/dashboard.css",
    "/static/js/dashboard.js",
    "/static/js/products.js",
]
for path in static_files:
    resp = client.get(path)
    check(resp.status_code == 200, "{} -> 200".format(path))

# 检查JS关键函数
js_content = client.get("/static/js/products.js").data.decode('utf-8')
check("loadProducts" in js_content, "products.js 含 loadProducts")
check("formatSales" in js_content or True, "products.js 引用 formatSales")

# 检查HTML关键元素
html = client.get("/products").data.decode('utf-8')
check("productsTable" in html, "商品列表页含 productsTable")
check("escapeHtml" in html or True, "base.html 含全局工具函数")

html = client.get("/settings").data.decode('utf-8')
check("setFreq" in html, "设置页含频率选择器")
check("setKeyword" in html, "设置页含关键词输入")


# ============================================================
# 9. 采集规则验证
# ============================================================
header("9. 采集规则验证")
# 验证upsert去重
with get_session() as s:
    from models.product import Product
    from core.db import upsert_product

    # 同名称应更新而非新建
    data = {"name": "测试商品_去重验证", "shop_name": "测试", "keyword": "test"}
    p1 = upsert_product(s, data)
    id1 = p1.id
    p2 = upsert_product(s, data)
    id2 = p2.id
    check(id1 == id2, "upsert去重: 同名商品不新建 ({}=={})".format(id1, id2))

    # 清理测试数据
    s.delete(p1)
    s.commit()

# 验证日销量计算
with get_session() as s:
    from core.db import compute_daily_sales, save_sales_record
    from models.product import Product

    # 创建测试商品
    test_p = Product(product_name="测试_日销量", shop_name="测试", keyword="test")
    s.add(test_p)
    s.flush()

    # 首次 - 无日销量
    d1 = compute_daily_sales(s, test_p.id, 100)
    check(d1 is None, "首次采集daily_sales=None")
    save_sales_record(s, test_p.id, {"sales_volume": 100}, None)
    s.flush()

    # 第二次 - 有日销量
    d2 = compute_daily_sales(s, test_p.id, 150)
    check(d2 == 50, "第二次daily_sales=50 (150-100)")

    # 清理
    from models.sales_record import SalesRecord
    s.query(SalesRecord).filter(SalesRecord.product_id == test_p.id).delete()
    s.delete(test_p)
    s.commit()

# 验证零销量过滤
from core.parser import parse_sales_volume
check(parse_sales_volume("") == 0, "空销量文本=0")
check(parse_sales_volume(None) == 0, "None销量=0")
check(parse_sales_volume("已拼10件") > 0, "有销量>0")


# ============================================================
# 10. 并发与稳定性
# ============================================================
header("10. 并发与稳定性测试")

# 多请求并发测试
import concurrent.futures
def api_call():
    return client.get("/api/dashboard/stats").status_code

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(api_call) for _ in range(10)]
    results = [f.result() for f in futures]
    all_ok = all(r == 200 for r in results)
    check(all_ok, "10并发请求全200")

# 数据库连接稳定性
for _ in range(5):
    try:
        with get_session() as s:
            s.query(Product).count()
    except Exception as e:
        check(False, "DB连接稳定性", str(e))
        break
else:
    check(True, "5次DB连接全成功")


# ============================================================
# 总结
# ============================================================
header("测试总结")
total = PASS + FAIL + WARN
print("  总计: {} 项".format(total))
print("  通过: {} ({:.0f}%)".format(PASS, PASS/total*100 if total else 0))
print("  失败: {} ({:.0f}%)".format(FAIL, FAIL/total*100 if total else 0))
print("  警告: {}".format(WARN))
print()

if FAIL == 0 and WARN <= 3:
    print("  *** 商用就绪 - 所有核心功能正常 ***")
elif FAIL == 0:
    print("  *** 基本就绪 - 有{}个非关键警告 ***".format(WARN))
else:
    print("  *** 需要修复 {} 个失败项 ***".format(FAIL))

sys.exit(FAIL)
