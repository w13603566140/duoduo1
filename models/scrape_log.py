"""
采集任务日志 ORM 模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from core.db import Base


class ScrapeLog(Base):
    """采集运行日志"""

    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False, default=datetime.now, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    status = Column(String(20), nullable=False, default="running", comment="状态: running/success/failed")
    products_found = Column(Integer, default=0, comment="发现商品数")
    records_saved = Column(Integer, default=0, comment="保存记录数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    keyword_used = Column(String(128), nullable=True, comment="使用的关键词")

    def __repr__(self):
        return f"<ScrapeLog(id={self.id}, status={self.status}, products={self.products_found})>"
