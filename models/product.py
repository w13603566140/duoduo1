"""
商品主表 ORM 模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, Text
from core.db import Base


class Product(Base):
    """拼多多商品"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pdd_product_id = Column(String(64), unique=True, nullable=True, comment="拼多多内部商品ID")
    product_name = Column(String(512), nullable=False, comment="商品标题")
    product_link = Column(String(1024), nullable=True, comment="商品/搜索链接")
    shop_name = Column(String(256), nullable=True, comment="店铺名称（从详情页提取）")
    keyword = Column(String(128), nullable=False, default="莜面鱼鱼", comment="搜索关键词")
    first_seen = Column(DateTime, nullable=False, default=datetime.now, comment="首次发现时间")
    last_seen = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="最近出现时间")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否仍在售")

    __table_args__ = (
        Index("idx_keyword", "keyword"),
        Index("idx_shop", "shop_name"),
        Index("idx_active", "is_active"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.product_name[:30]}...)>"
