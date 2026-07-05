"""
拼多多文本解析器 - 将采集到的原始文本解析为结构化数值
"""
import re
from typing import Optional
from decimal import Decimal, InvalidOperation


def parse_sales_volume(text: str) -> int:
    """
    解析拼多多销量文本为整数。

    支持格式:
        "已拼23件"         -> 23
        "已拼1,230件"      -> 1230
        "已拼1.2万件"      -> 12000
        "已拼10万件"       -> 100000
        "已拼10万+件"      -> 100000
        "已拼100万+件"     -> 1000000
        "已拼1.23万件"     -> 12300
        "" / None          -> 0
    """
    if not text:
        return 0

    text = text.strip()

    # 匹配 "X万" 或 "X万+" 模式
    wan_pattern = re.search(r"([\d,]+\.?\d*)\s*万", text)
    if wan_pattern:
        num_str = wan_pattern.group(1).replace(",", "")
        try:
            return int(float(num_str) * 10000)
        except ValueError:
            pass

    # 匹配 "X件" 或 "X+件" 模式
    jian_pattern = re.search(r"([\d,]+)\+?\s*件", text)
    if jian_pattern:
        num_str = jian_pattern.group(1).replace(",", "")
        try:
            return int(num_str)
        except ValueError:
            pass

    # 兜底：提取任意数字
    num_match = re.search(r"(\d[\d,]*)", text)
    if num_match:
        try:
            return int(num_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return 0


def parse_price(text: str) -> Optional[float]:
    """
    解析价格文本为浮点数。

    支持格式:
        "￥19.9"   -> 19.9
        "¥29.90"   -> 29.9
        "19.9"     -> 19.9
        "19.9元"   -> 19.9
        "" / None  -> None
    """
    if not text:
        return None

    text = text.strip()
    # 去掉货币符号和"元"
    text = re.sub(r"[￥¥元]", "", text).strip()
    # 去掉逗号（千分位分隔符）
    text = text.replace(",", "")

    # 提取数字部分
    match = re.search(r"(\d+\.?\d*)", text)
    if not match:
        return None

    try:
        price = Decimal(match.group(1))
        return float(round(price, 2))
    except InvalidOperation:
        return None


def parse_price_text(text: str) -> str:
    """获取价格原始文本（保留符号），用于展示"""
    if not text:
        return ""
    return text.strip()


def normalize_product_name(text: str) -> str:
    """清洗商品名称"""
    if not text:
        return ""
    # 去HTML实体（如 &#10; 换行符）
    import html
    text = html.unescape(text)
    # 去首尾空白，合并连续空白
    text = " ".join(text.split())
    # 截断至60字符（保留省略号）
    if len(text) > 60:
        text = text[:57] + "..."
    return text


def normalize_shop_name(text: str) -> str:
    """清洗店铺名称"""
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) > 256:
        text = text[:253] + "..."
    return text


def extract_shop_name(desc: str) -> str:
    """从商品描述/详情页描述中提取店铺名"""
    desc = desc.strip('[]')

    # 模式: 结尾包含"旗舰店"/"专卖店"/"官方店"等
    store_suffixes = ['旗舰店', '专卖店', '官方店', '企业店', '工厂店', '直营店', '专营店']
    for suffix in store_suffixes:
        if suffix in desc:
            idx = desc.find(suffix)
            end = idx + len(suffix)
            # 往前找品牌名开头（遇到空格或到字符串开头）
            start = idx
            while start > 0:
                c = desc[start - 1]
                if c in '，,。. 山西粗低手有' or desc[start-1:start+1] == '莜面':
                    break
                start -= 1
            shop = desc[start:end]
            shop = shop.strip('，,。. ')
            if len(shop) >= 2:
                return shop[:60]

    # 备用：取描述开头作为品牌名（不含产品关键词）
    for sep in ['有机', '山西', '正宗', '粗粮', '低脂']:
        if sep in desc:
            brand = desc.split(sep)[0].strip()
            if 2 <= len(brand) <= 15 and '莜面' not in brand:
                return brand

    return ''
