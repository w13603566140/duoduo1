"""
清空拼多多监控系统所有历史数据
用法: python clear_all_data.py
"""
import sqlite3
import os
import shutil
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'scraper.db')

if not os.path.exists(DB_PATH):
    print('数据库文件不存在:', DB_PATH)
    exit(1)

# 备份
backup_path = DB_PATH + '.backup.{}'.format(datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(DB_PATH, backup_path)
print('已备份数据库:', backup_path)

# 清空表
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('DELETE FROM sales_records')
cur.execute('DELETE FROM products')
cur.execute('DELETE FROM scrape_logs')
conn.commit()
conn.execute('VACUUM')
conn.close()

print('已清空: products, sales_records, scrape_logs')
print('数据库已重置，可以开始新的采集。')
