"""
每日销量快照 ORM 模型
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, ForeignKey, Index
from core.db import Base


class SalesRecord(Base):
    """每日销量记录"""

    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    scrape_time = Column(DateTime, nullable=False, default=datetime.now, comment="采集时间")
    scrape_date = Column(Date, nullable=False, comment="采集日期（用于分组）")
    price = Column(Float, nullable=True, comment="采集时价格")
    sales_volume = Column(Integer, nullable=False, default=0, comment="累计销量")
    daily_sales = Column(Integer, nullable=True, comment="估算日销量（与上一条记录的差值）")
    rank_position = Column(Integer, nullable=True, comment="搜索结果排名")
    raw_sales_text = Column(String(64), nullable=True, comment="原始销量文本")

    __table_args__ = (
        Index("idx_date", "scrape_date"),
        Index("idx_product_date", "product_id", "scrape_date"),
        Index("idx_volume", "sales_volume"),
    )

    def __repr__(self):
        return f"<SalesRecord(product_id={self.product_id}, date={self.scrape_date}, vol={self.sales_volume})>"
