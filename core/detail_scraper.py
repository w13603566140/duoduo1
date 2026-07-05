"""
点击商品详情页提取店铺名和单品销量
"""
import time
import re
import uiautomator2 as u2
from utils.logger import logger
from core.parser import extract_shop_name


def scrape_detail_page(device: u2.Device, card_bounds: tuple) -> dict:
    """
    点击商品卡片，进入详情页提取数据。
    返回 dict: {sales_text, shop_name}
    """
    x1, y1, x2, y2 = card_bounds
    cx = (x1 + x2) // 2
    cy = y1 + (y2 - y1) // 3

    device.click(cx, cy)
    time.sleep(5)

    result = {'sales_text': '', 'shop_name': ''}

    try:
        xml = device.dump_hierarchy()

        # 1. 单品销量: "已拼X万+盒" / "本店已拼X件" (仅过滤全网/全店总售)
        for m in re.finditer(r'<node[^>]*>', xml):
            full = m.group()
            text = re.search(r'text="([^"]*)"', full)
            if text and text.group(1):
                t = text.group(1)
                is_store_total = any(kw in t for kw in ['全网总售', '全网销量', '全店总售', '全店销量', '店铺总售'])
                if not is_store_total and re.search(r'已拼[\d,.]+万?\+?[件盒箱袋]', t):
                    result['sales_text'] = t
                    break

        # 2. 店铺名: 从商品描述content-desc中提取
        desc_match = re.search(r'content-desc="([^"]{20,300})"', xml)
        if desc_match:
            desc = desc_match.group(1)
            if 'WLAN' not in desc and '手机信号' not in desc:
                shop = extract_shop_name(desc)
                if shop:
                    result['shop_name'] = shop

    except Exception as e:
        logger.warning('详情页提取异常: {}'.format(e))

    device.press('back')
    time.sleep(2)

    return result
