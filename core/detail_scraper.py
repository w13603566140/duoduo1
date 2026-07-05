"""
点击商品详情页提取店铺名和单品销量
"""
import time
import re
import uiautomator2 as u2
from utils.logger import logger


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
                shop = _extract_shop_name(desc)
                if shop:
                    result['shop_name'] = shop

    except Exception as e:
        logger.warning('详情页提取异常: {}'.format(e))

    device.press('back')
    time.sleep(2)

    return result


def _extract_shop_name(desc: str) -> str:
    """从详情页描述提取店铺名"""
    desc = desc.strip('[]')

    # 模式: 结尾包含"旗舰店"/"专卖店"/"官方店"等
    store_suffixes = ['旗舰店', '专卖店', '官方店', '企业店', '工厂店', '直营店', '专营店']
    for suffix in store_suffixes:
        if suffix in desc:
            # 截取旗舰店及其前面的品牌名
            idx = desc.find(suffix)
            end = idx + len(suffix)
            # 往前找品牌名开头（遇到空格或到字符串开头）
            start = idx
            while start > 0:
                c = desc[start - 1]
                # 遇到分隔符或产品关键词时停止
                if c in '，,。. 山西粗低手有' or desc[start-1:start+1] == '莜面':
                    break
                start -= 1
            shop = desc[start:end]
            shop = shop.strip('，,。. ')
            if len(shop) >= 2:
                return shop[:60]

    # 备用：取描述开头作为品牌名（不含产品关键词）
    # 如 "野禾有机莜面鱼鱼..." -> "野禾"
    for sep in ['有机', '山西', '正宗', '粗粮', '低脂']:
        if sep in desc:
            brand = desc.split(sep)[0].strip()
            if 2 <= len(brand) <= 15 and '莜面' not in brand:
                return brand

    return ''
