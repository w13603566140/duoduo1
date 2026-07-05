"""
工具函数：日期处理、文本清洗、重试装饰器
"""
import time
import functools
from datetime import date, datetime
from typing import Callable, TypeVar

from .logger import logger

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    重试装饰器，支持指数退避。
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    logger.warning(
                        f"{func.__name__} 第{attempt}次尝试失败: {e}"
                    )
                    if attempt < max_attempts:
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_error  # type: ignore

        return wrapper

    return decorator


def normalize_text(text: str, max_length: int = 512) -> str:
    """清洗文本：去首尾空白、合并连续空白、截断"""
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text


def today_str() -> str:
    """返回今天的日期字符串 YYYY-MM-DD"""
    return date.today().isoformat()


def now_str() -> str:
    """返回当前时间字符串 YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
