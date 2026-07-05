"""
精准采集：从搜索列表取商品名+价格，点击详情页取准确销量
"""
import sys, os, time, random, re
sys.path.insert(0, os.path.dirname(__file__))

import uiautomator2 as u2
from core.db import init_db, get_session, create_scrape_log, finish_scrape_log
from core.db import upsert_product, compute_daily_sales, save_sales_record
from core.parser import parse_sales_volume, parse_price, normalize_product_name
from core.scraper import perform_search, extract_all_text_with_positions, parse_product_cards
from config import config
from utils.logger import logger

MAX_DETAIL_CLICKS = 50  # 最多点击详情页数量


def get_detail_sales(device: u2.Device) -> dict:
    """点击当前搜索结果页第一个可见卡片，进入详情页获取准确销量"""
    # 获取可见卡片位置
    xml = device.dump_hierarchy()
    cards = []
    for m in re.finditer(r'<node[^>]*clickable="true"[^>]*>', xml):
        full = m.group()
        bounds = re.search(r'bounds="([^"]+)"', full)
        if bounds:
            b = bounds.group(1)
            parts = b.replace('][', ',').replace('[', '').replace(']', '').split(',')
            if len(parts) == 4:
                w = int(parts[2]) - int(parts[0])
                h = int(parts[3]) - int(parts[1])
                if w > 200 and h > 200:
                    cards.append((int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])))

    if not cards:
        return {}

    # 点击第一个卡片
    x1, y1, x2, y2 = cards[0]
    cx = (x1 + x2) // 2
    cy = y1 + (y2 - y1) // 3
    device.click(cx, cy)
    time.sleep(5)

    result = {}
    try:
        xml = device.dump_hierarchy()

        # 提取销量文本
        for m in re.finditer(r'<node[^>]*>', xml):
            full = m.group()
            text = re.search(r'text="([^"]*)"', full)
            if text and text.group(1):
                t = text.group(1)
                # 单品销量（排除全网/全店总售）
                is_store = any(kw in t for kw in ['全网总售', '全网销量', '全店总售', '全店销量', '店铺总售'])
                if not is_store and re.search(r'已拼[\d,.]+万?\+?[件盒箱袋]', t):
                    result['sales_text'] = t
                    break

        # 提取店铺名
        desc_match = re.search(r'content-desc="([^"]{20,300})"', xml)
        if desc_match:
            desc = desc_match.group(1)
            if 'WLAN' not in desc and '手机信号' not in desc:
                for suffix in ['旗舰店', '专卖店', '官方店', '企业店', '工厂店', '直营店']:
                    if suffix in desc:
                        idx = desc.find(suffix)
                        start = max(0, idx - 15)
                        shop = desc[start:idx + len(suffix)].strip('[],. ')
                        if len(shop) >= 2:
                            result['shop_name'] = shop[:60]
                            break
    except Exception as e:
        logger.warning('详情提取异常: {}'.format(e))

    # 返回
    device.press('back')
    time.sleep(2)
    return result


def run():
    init_db()
    keyword = config.search_keyword
    device = u2.connect(config.device_serial or None)

    logger.info('=' * 50)
    logger.info('精准采集: keyword={}'.format(keyword))
    logger.info('=' * 50)

    # 第一步：搜索并收集商品名+价格（快速）
    if not perform_search(device, keyword):
        logger.error('搜索失败')
        return

    with get_session() as session:
        log_entry = create_scrape_log(session, keyword)
        log_id = log_entry.id

        # 第二步：快速滚动收集所有商品名+价格
        all_names = set()
        all_products = []
        scroll = 0

        while scroll < config.max_scrolls and len(all_products) < 200:
            items = extract_all_text_with_positions(device)
            cards = parse_product_cards(items)

            for card in cards:
                name = normalize_product_name(card.get('name', ''))
                if not name or name in all_names:
                    continue
                all_names.add(name)
                all_products.append({
                    'name': name,
                    'price': parse_price(card.get('price_text', '')),
                })

            logger.info('  滚动{}: 累计{}个商品'.format(scroll + 1, len(all_products)))

            if len(cards) == 0:
                break

            # 滚动
            device.swipe(450, 1100, 450, 300, duration=0.5)
            time.sleep(config.scroll_pause_seconds)
            scroll += 1

        logger.info('商品名收集完成: {}个'.format(len(all_products)))

        # 第三步：回到顶部，逐个点击详情页取销量
        for _ in range(min(scroll + 2, 20)):
            device.swipe(450, 300, 450, 1200, duration=0.3)
            time.sleep(0.3)

        detail_data = {}
        for i in range(min(len(all_products), MAX_DETAIL_CLICKS)):
            try:
                detail = get_detail_sales(device)
                if detail.get('sales_text'):
                    # 将销量关联到当前可见的第一个商品
                    # 重新获取当前可见商品
                    items = extract_all_text_with_positions(device)
                    cards = parse_product_cards(items)
                    if cards:
                        current_name = normalize_product_name(cards[0].get('name', ''))
                        detail_data[current_name] = detail
                        logger.info('  [{}/{}] {} -> {}'.format(
                            i + 1, min(len(all_products), MAX_DETAIL_CLICKS),
                            current_name[:30], detail.get('sales_text', '?')[:30]))
            except Exception as e:
                logger.warning('  详情{}失败: {}'.format(i + 1, e))
                try:
                    device.press('back')
                    time.sleep(1.5)
                except:
                    pass

        # 第四步：保存
        records_saved = 0
        for prod in all_products:
            name = prod['name']
            detail = detail_data.get(name, {})

            parsed = {
                'name': name,
                'shop_name': detail.get('shop_name', ''),
                'price': prod.get('price'),
                'sales_volume': parse_sales_volume(detail.get('sales_text', '')),
                'raw_sales_text': detail.get('sales_text', ''),
                'rank_position': 0,
                'keyword': keyword,
                'product_link': 'https://mobile.yangkeduo.com/search_result.html?search_key={}'.format(keyword),
            }

            # 零销量跳过
            if parsed['sales_volume'] <= 0:
                continue

            product = upsert_product(session, parsed)
            daily = compute_daily_sales(session, product.id, parsed['sales_volume'])
            save_sales_record(session, product.id, parsed, daily)
            records_saved += 1

        finish_scrape_log(session, log_id, status='success',
                          products_found=records_saved, records_saved=records_saved)

        logger.info('精准采集完成: {}个商品'.format(records_saved))
        return {'success': True, 'products': records_saved}


if __name__ == '__main__':
    run()
