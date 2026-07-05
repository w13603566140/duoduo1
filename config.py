"""
集中配置管理 - 从环境变量读取所有配置项
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """应用配置单例"""

    # === MySQL配置 ===
    mysql_host: str = os.getenv("MYSQL_HOST", "")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "pdd_monitor")

    # === 设备配置 ===
    device_serial: str = os.getenv("DEVICE_SERIAL", "")  # 空=USB自动检测

    # === 采集配置 ===
    search_keyword: str = os.getenv("SEARCH_KEYWORD", "莜面鱼鱼")
    max_scrolls: int = int(os.getenv("MAX_SCROLLS", "20"))
    scroll_pause_seconds: float = float(os.getenv("SCROLL_PAUSE_SECONDS", "2"))
    max_results: int = int(os.getenv("MAX_RESULTS", "200"))

    # === 定时任务 ===
    scrape_cron: str = os.getenv("SCRAPE_CRON", "0 2 * * *")

    # === Web服务 ===
    web_host: str = os.getenv("WEB_HOST", "0.0.0.0")
    web_port: int = int(os.getenv("WEB_PORT", "5000"))
    web_debug: bool = os.getenv("WEB_DEBUG", "false").lower() == "true"

    # === ADB ===
    adb_path: str = os.getenv("ADB_PATH", "")

    # === 拼多多APP ===
    pdd_package: str = "com.xunmeng.pinduoduo"

    @property
    def use_mysql(self) -> bool:
        """是否使用MySQL（否则使用SQLite）"""
        return bool(self.mysql_host and self.mysql_user)

    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        if self.use_mysql:
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
                "?charset=utf8mb4"
            )
        # SQLite 回退
        db_path = os.path.join(os.path.dirname(__file__), "data", "scraper.db")
        return f"sqlite:///{db_path}"


# 全局配置实例
config = Config()
