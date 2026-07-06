"""
拼多多采集引擎 - 基于实测UI适配PDD 8.14版本
"""
import time
import random
import re
from typing import Optional

import uiautomator2 as u2

from config import config
from utils.logger import logger


# === 真人行为模拟 ===

def human_delay(min_s=0.5, max_s=2.0):
    """随机延迟，模拟真人操作间隔"""
    time.sleep(random.uniform(min_s, max_s))


def human_swipe(device: u2.Device):
    """模拟一次真人滑动浏览"""
    w, h = device.window_size()
    sx = w // 2 + random.randint(-30, 30)
    sy = int(h * 0.7) + random.randint(-50, 50)
    ey = int(h * 0.3) + random.randint(-50, 50)
    device.swipe(sx, sy, sx, ey, duration=random.uniform(0.4, 0.8))


def human_tap(device: u2.Device, x: int, y: int):
    """在目标附近随机偏移点击"""
    cx = x + random.randint(-12, 12)
    cy = y + random.randint(-8, 8)
    device.click(cx, cy)


# === 弹窗处理 ===

def dismiss_popups(device: u2.Device):
    """尝试关闭常见弹窗"""
    # 按返回键
    try:
        device.press('back')
        time.sleep(0.5)
    except:
        pass


# === 搜索流程 ===

def perform_search(device: u2.Device, keyword: str) -> bool:
    """
    在拼多多中执行搜索。使用极慢速真人模式避免反爬。
    适配 PDD 8.14 版本。
    """
    logger.info('启动拼多多并搜索: {}'.format(keyword))

    # 1. 启动APP
    device.app_stop(config.pdd_package)
    human_delay(3, 5)
    device.app_start(config.pdd_package)
    logger.info('等待首页加载...')
    human_delay(8, 12)

    # 2. 模拟浏览行为
    human_swipe(device)
    human_delay(2, 3)
    human_swipe(device)
    human_delay(1.5, 2.5)

    # 3. 点击搜索区域（文本区域，不是相机图标）
    logger.info('打开搜索页面...')
    human_tap(device, 400, 73)
    human_delay(4, 6)

    # 4. 查找搜索输入框
    si = device(
        resourceId='com.xunmeng.pinduoduo:id/pdd',
        className='android.widget.EditText'
    )
    if not si.exists(timeout=3):
        # 回退：可能还在首页，再点一次
        logger.warning('未找到搜索框，重试...')
        human_tap(device, 350, 73)
        human_delay(3, 5)
        if not si.exists(timeout=3):
            logger.error('无法找到搜索输入框')
            device.screenshot('logs/search_error.png')
            return False

    # 5. 反复清空旧文本（兼容输入框残留）
    si.click()
    human_delay(0.5, 1.0)
    # 多次清空确保旧文本被删掉
    for _ in range(3):
        si.set_text('')
        human_delay(0.3, 0.5)

    # 6. 输入关键词，并验证
    logger.info('输入关键词: {}'.format(keyword))
    si.set_text(keyword)
    human_delay(1.5, 2.5)

    # 验证输入框内容
    try:
        actual_text = si.get_text()
        if keyword not in actual_text:
            logger.warning('输入框内容不匹配: {} vs {}'.format(actual_text, keyword))
            si.set_text('')
            human_delay(0.5, 1.0)
            si.set_text(keyword)
            human_delay(1, 2)
    except:
        pass

    # 7. 按回车搜索
    logger.info('执行搜索...')
    device.press('enter')
    logger.info('等待搜索结果加载...')
    human_delay(10, 15)

    # 8. 检查状态
    xml = device.dump_hierarchy()
    if '系统繁忙' in xml or '网络异常' in xml or '稍后再试' in xml:
        logger.error('搜索被拦截（系统繁忙）')
        device.screenshot('logs/blocked.png')
        return False

    # 验证搜索结果包含关键词
    if keyword not in xml:
        logger.warning('搜索结果未检测到关键词 {}，尝试重新搜索'.format(keyword))
        device.screenshot('logs/search_verify_fail.png')
        # 再试一次：从搜索栏重新搜索
        try:
            si2 = device(resourceId='com.xunmeng.pinduoduo:id/pdd', className='android.widget.EditText')
            if si2.exists(timeout=2):
                si2.click()
                human_delay(0.5, 1.0)
                si2.set_text('')
                human_delay(0.3, 0.5)
                si2.set_text(keyword)
                human_delay(1, 2)
                device.press('enter')
                human_delay(10, 15)
        except:
            pass

    return True


# === 商品卡片提取 ===

def extract_all_text_with_positions(device: u2.Device) -> list:
    """提取当前屏幕所有文本及其位置（同时读取 text 和 content-desc）"""
    xml = device.dump_hierarchy()
    items = []
    for m in re.finditer(r'<node[^>]*>', xml):
        full = m.group()
        text = re.search(r'text="([^"]+)"', full)
        desc = re.search(r'content-desc="([^"]+)"', full)
        rid = re.search(r'resource-id="([^"]*)"', full)
        bounds = re.search(r'bounds="([^"]+)"', full)

        t = text.group(1) if text and text.group(1) else ''
        d = desc.group(1) if desc and desc.group(1) else ''

        # 优先使用更长的文本（content-desc 通常是完整标题，text 可能被截断）
        display_text = d if len(d) > len(t) else t
        if not display_text or len(display_text) <= 1:
            continue

        r = rid.group(1) if rid else ''
        b = bounds.group(1) if bounds else ''
        parts = b.replace('][', ',').replace('[', '').replace(']', '').split(',')
        if len(parts) == 4:
            items.append({
                'text': t,
                'desc': d,
                'y': int(parts[1]),
                'x': int(parts[0]),
                'id': r,
            })
    items.sort(key=lambda x: (x['y'], x['x']))
    return items


def _is_product_name(text: str) -> bool:
    """判断文本是否为商品名（排除标签/元数据文本）"""
    if not text or len(text) < 6:
        return False
    # 排除已知的非商品名模式
    noise_patterns = [
        r'^\d+人收藏$',
        r'^\d+\.?\d*万人收藏$',
        r'^近\d+天\d+%好评$',
        r'^本店已拼[\d.]+万?件$',
        r'^已拼[\d.]+万?\+?件$',
        r'^全网总[售销][\d.]+万?\+?件$',
        r'^全网销量[\d.]+万?\+?件$',
        r'^退货包运费$',
        r'^运费险$',
        r'^极速退款$',
        r'^坏了包赔$',
        r'^正品保证$',
        r'^假一赔十$',
        r'^24小时发货$',
        r'^先用后付$',
        r'^未发货.*$',
        r'^\d+小时.*$',
        r'^券后\d+\.?\d*$',
        r'^满\d+减\d+$',
        r'^.*省\d+元$',
        r'^\d+$',
        r'^全场随.*$',
        r'^新品.*$',
        r'^品牌.*$',
        r'^进口.*$',
        r'^顺丰.*$',
        r'^次日.*$',
        r'^48小时.*$',
        r'^保税.*$',
        r'^现货.*$',
        r'^限时.*$',
        r'^.{1,3}$',  # 1-3个字符
    ]
    for pat in noise_patterns:
        if re.match(pat, text):
            return False
    return True


def parse_product_cards(items: list) -> list:
    """
    解析商品卡片。PDD搜索结果使用2列网格布局（屏幕宽900px，列分界~450px）。
    每个卡片：名称(y) → 标签(y+30) → 价格(y+65) → 销量(y+70)
    关键：必须按X坐标区分左右列，避免跨列关联价格/销量。
    """
    from core.parser import extract_shop_name

    # 找出候选商品名：含「莜面鱼」或「莜面」+「鱼」
    candidate_names = []
    for i, item in enumerate(items):
        t = item['text']
        d = item.get('desc', '')
        # content-desc 通常是完整标题，text 可能被截断
        full_title = d if len(d) > len(t) else t
        y = item['y']
        x = item['x']
        # 过滤：必须在商品区(y>200)，含莜面鱼关键词，6字以上
        if y > 200 and ('莜面鱼' in full_title or ('莜面' in full_title and '鱼' in full_title)) and len(full_title) >= 6:
            candidate_names.append({'idx': i, 'name': full_title, 'desc': d, 'y': y, 'x': x})

    products = []
    seen_keys = set()

    for cand in candidate_names:
        i = cand['idx']
        y = cand['y']
        x = cand['x']
        name = cand['name']
        desc = cand.get('desc', '')

        # 去重
        key = name[:50]
        if key in seen_keys:
            continue

        # 确定列：左列x<450，右列x>=450
        is_left = x < 450

        prod = {'name': name, 'desc': desc, 'y_start': y, 'y_end': y}

        # 向下搜索，只取同列元素（X坐标相近）
        for j in range(i + 1, min(i + 20, len(items))):
            t2 = items[j]['text']
            y2 = items[j]['y']
            x2 = items[j]['x']

            # 超过卡片垂直范围
            if y2 - y > 150:
                break

            # 检查同列：左列x2<450，右列x2>=450
            same_column = (is_left and x2 < 450) or (not is_left and x2 >= 450)
            if not same_column:
                continue

            # 价格：纯数字 1<len<8
            if 'price_text' not in prod and re.match(r'^\d+\.?\d*$', t2) and 1 < len(t2) < 8:
                prod['price_text'] = t2
                prod['y_end'] = max(prod['y_end'], y2)
                continue

            # 销量：只取单品「已拼」，跳过「全网总售/全网销量」店铺级数据
            # 「本店已拼」仍是单品销量(该商品在此店的销量)，保留
            if 'sales_text' not in prod:
                # 仅过滤全店铺级别的销量
                is_store_total = False
                for kw in ['全网总售', '全网销量', '全店总售', '全店销量', '店铺总售']:
                    if kw in t2:
                        is_store_total = True
                        break
                if is_store_total:
                    continue
                # 单品销量：「已拼X件」「本店已拼X件」
                if re.search(r'已拼[\d,.]+\+?[件盒箱袋]', t2) or re.search(r'已拼[\d,.]+万', t2):
                    prod['sales_text'] = t2
                    prod['y_end'] = max(prod['y_end'], y2)
                    continue

        # 从完整描述中提取店铺名
        if desc:
            shop = extract_shop_name(desc)
            if shop:
                prod['shop_name'] = shop

        # 至少要有价格或销量
        if 'price_text' in prod or 'sales_text' in prod:
            seen_keys.add(key)
            products.append(prod)

    return products


def scrape_all_results(device: u2.Device) -> list:
    """滚动加载并采集所有搜索结果"""
    all_products = []
    seen_names = set()
    scroll_count = 0
    no_new_count = 0

    while scroll_count < config.max_scrolls:
        logger.info('--- 第 {} 次采集 ---'.format(scroll_count + 1))

        # 提取当前可见商品
        items = extract_all_text_with_positions(device)
        cards = parse_product_cards(items)

        new_count = 0
        for card in cards:
            name = card.get('name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                all_products.append(card)
                new_count += 1

        logger.info('  新增 {} 个，累计 {} 个'.format(new_count, len(all_products)))

        if new_count == 0:
            no_new_count += 1
            if no_new_count >= 3:
                logger.info('连续无新商品，停止滚动')
                break
        else:
            no_new_count = 0

        if len(all_products) >= config.max_results:
            break

        # 滚动加载更多
        human_swipe(device)
        human_delay(config.scroll_pause_seconds, config.scroll_pause_seconds + 1)

        scroll_count += 1

    return all_products


# === 深度规格采集 ===

def _deep_scrape_specs(device: u2.Device, session, keyword: str) -> int:
    """点击详情页提取店铺名和单品销量"""
    from models.product import Product
    from core.detail_scraper import scrape_detail_page

    # 找缺少店铺名的商品（限4个）
    products = (
        session.query(Product)
        .filter((Product.shop_name == '') | (Product.shop_name == None))
        .order_by(Product.id)
        .limit(4)
        .all()
    )

    if not products:
        return 0

    logger.info('深度采集店铺名 (最多{}个)...'.format(len(products)))

    # 回到搜索结果顶部
    for _ in range(6):
        device.swipe(450, 300, 450, 1200, duration=0.3)
        time.sleep(0.4)

    # 逐个点击可见卡片
    updated = 0
    card_positions = [
        (0, 233, 448, 797),
        (452, 233, 900, 797),
        (0, 802, 448, 1366),
        (452, 802, 900, 1366),
    ]

    for card_bounds in card_positions:
        if updated >= len(products):
            break
        try:
            detail = scrape_detail_page(device, card_bounds)
            p = products[updated]

            if detail.get('shop_name'):
                p.shop_name = detail['shop_name'][:256]

            if detail.get('sales_text'):
                from core.parser import parse_sales_volume
                vol = parse_sales_volume(detail['sales_text'])
                from models.sales_record import SalesRecord
                latest = (
                    session.query(SalesRecord)
                    .filter(SalesRecord.product_id == p.id)
                    .order_by(SalesRecord.scrape_time.desc())
                    .first()
                )
                if latest and vol > 0:
                    latest.sales_volume = vol
                    latest.raw_sales_text = detail['sales_text']

            updated += 1
            session.flush()
            logger.info('  [{}] shop={} sales={}'.format(
                p.id, detail.get('shop_name', '?')[:30], detail.get('sales_text', '?')[:30]))

        except Exception as e:
            logger.warning('  失败: {}'.format(e))
            try:
                device.press('back')
                time.sleep(1.5)
            except:
                pass

    session.commit()
    logger.info('店铺名采集完成: {}个'.format(updated))
    return updated


def _find_product_card_bounds(xml: str, name_fragment: str) -> tuple:
    """在XML中查找商品卡片位置"""
    # 查找包含商品名的可点击卡片
    import re as _re
    for m in _re.finditer(r'<node[^>]*clickable=\"true\"[^>]*>', xml):
        full = m.group()
        bounds = _re.search(r'bounds=\"([^\"]+)\"', full)
        if bounds:
            b = bounds.group(1)
            parts = b.replace('][', ',').replace('[', '').replace(']', '').split(',')
            if len(parts) == 4:
                w = int(parts[2]) - int(parts[0])
                h = int(parts[3]) - int(parts[1])
                if w > 200 and h > 150:  # 产品卡片尺寸
                    return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
    return None


def _scrape_detail_product(device: u2.Device, idx: int, total: int, start_time: float) -> dict:
    """
    点击当前屏幕第一个可见商品卡片，进入详情页提取数据。
    提取完成后返回搜索结果页。
    返回 dict 或 None（失败时）。
    """
    from core.link_extractor import extract_product_link
    from core.parser import extract_shop_name, normalize_product_name

    result = {'title': '', 'shop_name': '', 'link': ''}

    try:
        # 点击第一个可见卡片
        device.click(224, 500)
        time.sleep(4)

        # 超时检查
        elapsed = time.time() - start_time
        detail_timeout = getattr(config, 'detail_timeout', 60)
        if elapsed > detail_timeout * total:
            logger.warning('  [{}] 已达总超时限制，停止详情提取'.format(idx + 1))
            return None

        xml = device.dump_hierarchy()

        # 提取完整标题和店铺名
        desc_match = re.search(r'content-desc="([^"]{15,200})"', xml)
        if desc_match:
            desc = desc_match.group(1)
            if 'WLAN' not in desc and '信号' not in desc and '充电' not in desc:
                raw_title = desc.strip('[]').split('\n')[0]
                result['title'] = normalize_product_name(raw_title)
                result['shop_name'] = extract_shop_name(desc)

        # 提取真实链接
        link = extract_product_link(device)
        if link and 'goods' in link:
            result['link'] = link[:1024]

    except Exception as e:
        logger.warning('  详情提取异常: {}'.format(e))

    # 确保返回搜索结果页
    try:
        device.press('back')
        time.sleep(1.0)
    except:
        pass

    return result


def extract_all_product_details(device: u2.Device, session, max_count: int = 0) -> dict:
    """
    对所有商品逐一进入详情页，提取完整标题、店铺名、真实链接。
    返回 dict: {links_updated, shops_updated, titles_updated, failed}
    """
    from models.product import Product
    from core.parser import extract_shop_name, normalize_product_name

    if max_count <= 0:
        max_count = getattr(config, 'max_detail_extract', 200)

    products = (
        session.query(Product)
        .order_by(Product.last_seen.desc())
        .limit(max_count)
        .all()
    )

    if not products:
        return {'links_updated': 0, 'shops_updated': 0, 'titles_updated': 0, 'failed': 0}

    total = len(products)
    logger.info('=' * 50)
    logger.info('开始逐商品详情页采集 (共{}个商品)...'.format(total))
    logger.info('每个商品约15-20秒，预计总耗时{}分钟'.format(round(total * 17 / 60, 1)))
    logger.info('=' * 50)

    # 回到搜索列表并锚定顶部
    logger.info('锚定搜索列表顶部...')
    for _ in range(6):
        device.swipe(450, 300, 450, 1200, duration=0.3)
        time.sleep(0.2)
    time.sleep(1.0)

    links_updated = 0
    shops_updated = 0
    titles_updated = 0
    failed = 0
    start_time = time.time()
    row_height = 600  # 每个卡片行大约高度

    for idx, p in enumerate(products):
        # 进度日志（每5个或第一个/最后一个时输出）
        if idx % 5 == 0 or idx == total - 1:
            elapsed_min = (time.time() - start_time) / 60
            eta_min = max(0, (elapsed_min / max(idx, 1)) * (total - idx))
            logger.info('  进度: [{}/{}] ({}%) | 已用 {:0.1f}分 | 预计剩余 {:0.1f}分'.format(
                idx + 1, total, round((idx + 1) / total * 100),
                elapsed_min, eta_min))

        # 锚定位置：向上回顶，再向下滑到目标行
        if idx > 0:
            # 向上滑回顶
            for _ in range(6):
                device.swipe(450, 300, 450, 1200, duration=0.2)
                time.sleep(0.15)
            time.sleep(0.3)

            # 向下滑到已处理位置之后
            scroll_amount = min(idx * (row_height // 2), total * row_height)
            # 等价于往下滑过 idx 行卡片
            swipe_count = min(idx, 20)  # 最多滑20次，避免过度
            for _ in range(swipe_count):
                device.swipe(450, 800, 450, 400, duration=0.2)
                time.sleep(0.15)
            time.sleep(0.5)

        # 提取详情页数据
        detail = _scrape_detail_product(device, idx, total, start_time)
        if detail is None:
            failed += 1
            continue

        # 更新商品数据
        has_update = False

        if detail.get('title'):
            title = normalize_product_name(detail['title'])
            if len(title) >= 6 and len(title) > len(p.product_name or ''):
                p.product_name = title
                titles_updated += 1
                has_update = True

        if detail.get('shop_name') and not p.shop_name:
            p.shop_name = detail['shop_name'][:256]
            shops_updated += 1
            has_update = True

        if detail.get('link'):
            p.product_link = detail['link']
            links_updated += 1
            has_update = True

        if has_update:
            session.flush()

        # 真人延迟
        human_delay(2, 4)

    session.commit()

    total_time = (time.time() - start_time) / 60
    logger.info('=' * 50)
    logger.info('详情页采集完成: {}分钟后'.format(round(total_time, 1)))
    logger.info('  链接更新: {}/{} | 店铺更新: {}/{} | 标题更新: {}/{} | 失败: {}'.format(
        links_updated, total, shops_updated, total, titles_updated, total, failed))
    logger.info('=' * 50)

    return {
        'links_updated': links_updated,
        'shops_updated': shops_updated,
        'titles_updated': titles_updated,
        'failed': failed,
    }


# === 主采集流程 ===

def run_scrape(keyword: str = None, device_serial: str = None) -> dict:
    """完整采集流程"""
    if keyword is None:
        keyword = config.search_keyword

    logger.info('=' * 50)
    logger.info('开始采集: keyword={}'.format(keyword))
    logger.info('=' * 50)

    from core.db import (
        get_session, create_scrape_log, finish_scrape_log,
        upsert_product, compute_daily_sales, save_sales_record,
    )
    from core.parser import parse_sales_volume, parse_price, normalize_product_name, normalize_shop_name

    # 连接设备
    try:
        serial = device_serial or config.device_serial
        if serial:
            device = u2.connect(serial)
        else:
            device = u2.connect_usb()
        logger.info('设备连接成功: {}'.format(serial or 'USB'))
    except Exception as e:
        logger.error('设备连接失败: {}'.format(e))
        return {'success': False, 'error': str(e)}

    log_id = None

    try:
        # 执行搜索
        if not perform_search(device, keyword):
            return {'success': False, 'error': '搜索失败'}

        # 滚动采集
        raw_products = scrape_all_results(device)

        # 解析并入库
        with get_session() as session:
            log_entry = create_scrape_log(session, keyword)
            log_id = log_entry.id
            records_saved = 0
            skipped_zero = 0

            for i, raw in enumerate(raw_products):
                price_text = raw.get('price_text', '')
                sales_text = raw.get('sales_text', '')
                name = normalize_product_name(raw.get('name', ''))

                if not name:
                    continue

                sales_vol = parse_sales_volume(sales_text)
                # 累计销量为0的不采集（无单品销量数据）
                if sales_vol <= 0:
                    skipped_zero += 1
                    continue

                parsed = {
                    'name': name,
                    'shop_name': normalize_shop_name(raw.get('shop_name', '')),
                    'price': parse_price(price_text),
                    'sales_volume': sales_vol,
                    'raw_sales_text': sales_text,
                    'rank_position': i + 1,
                    'keyword': keyword,
                    'product_link': 'https://mobile.yangkeduo.com/search_result.html?search_key={}'.format(name[:30]),
                }

                product = upsert_product(session, parsed)
                daily = compute_daily_sales(session, product.id, parsed['sales_volume'])
                save_sales_record(session, product.id, parsed, daily)
                records_saved += 1

            logger.info('跳过{}个无销量商品'.format(skipped_zero))

            # 对所有商品逐一进入详情页提取完整标题、店铺名、真实链接
            detail_result = extract_all_product_details(device, session)

            finish_scrape_log(
                session, log_id,
                status='success',
                products_found=records_saved,
                records_saved=records_saved,
            )

            result = {
                'success': True,
                'log_id': log_id,
                'products_found': records_saved,
                'records_saved': records_saved,
                'skipped_zero': skipped_zero,
                'links_updated': detail_result.get('links_updated', 0),
                'shops_updated': detail_result.get('shops_updated', 0),
                'titles_updated': detail_result.get('titles_updated', 0),
                'detail_failed': detail_result.get('failed', 0),
            }

            logger.info('采集完成: {}'.format(result))
            return result

    except Exception as e:
        logger.error('采集失败: {}'.format(e))

        try:
            if log_id:
                with get_session() as session:
                    finish_scrape_log(
                        session, log_id,
                        status='failed',
                        error_message=str(e),
                    )
        except:
            pass

        return {'success': False, 'error': str(e)}
