"""
采集脚本：搜索结果快速采集（已验证可靠）
每商品: 从搜索结果提取标题+销量+价格，X列匹配，店铺销量过滤
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from core.db import init_db
from core.scraper import run_scrape

init_db()
result = run_scrape()
print('Result:', result)
