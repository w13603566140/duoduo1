"""Run a single scrape"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from core.db import init_db
from core.scraper import run_scrape

init_db()
result = run_scrape(keyword='莜面鱼鱼', device_serial='emulator-5554')
print('Result:', result)
