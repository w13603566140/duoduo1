"""
拼多多采集系统诊断工具
用法: python diagnose.py

诊断完成后，请把 logs/ 目录下生成的 diagnose_*.txt 文件发给我。
"""
import os
import sys
import time
import re
import datetime
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

TS = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def log(section, msg):
    print(f"[{section}] {msg}")

# ============ 1. 环境检查 ============
print("=" * 60)
print("拼多多采集系统诊断")
print("=" * 60)

try:
    import uiautomator2 as u2
    log("环境", "uiautomator2 已安装")
except Exception as e:
    log("环境", f"uiautomator2 导入失败: {e}")
    sys.exit(1)

try:
    import adbutils
    log("环境", "adbutils 已安装")
except Exception as e:
    log("环境", f"adbutils 导入失败: {e}")
    sys.exit(1)

try:
    from config import config
    log("配置", f"设备序列号: {config.device_serial}")
    log("配置", f"搜索关键词: {config.search_keyword}")
except Exception as e:
    log("配置", f"读取配置失败: {e}")

# ============ 2. ADB 设备检查 ============
print("\n" + "=" * 60)
print("ADB 设备检查")
print("=" * 60)

try:
    client = adbutils.AdbClient()
    devices = client.device_list()
    log("ADB", f"发现设备数量: {len(devices)}")
    for d in devices:
        log("ADB", f"  设备: {d.serial}")
except Exception as e:
    log("ADB", f"获取设备列表失败: {e}")
    devices = []

# 尝试连接配置中的设备
serial = config.device_serial or '127.0.0.1:5555'
adb_device = None
try:
    adb_device = client.device(serial)
    log("ADB", f"成功连接设备: {serial}")
except Exception as e:
    log("ADB", f"连接设备 {serial} 失败: {e}")
    if devices:
        try:
            serial = devices[0].serial
            adb_device = client.device(serial)
            log("ADB", f"回退连接第一个设备: {serial}")
        except Exception as e2:
            log("ADB", f"回退连接也失败: {e2}")

# ============ 3. uiautomator2 连接检查 ============
print("\n" + "=" * 60)
print("uiautomator2 连接检查")
print("=" * 60)

u2_device = None
try:
    u2_device = u2.connect(serial)
    info = u2_device.info
    log("U2", f"连接成功: {serial}")
    log("U2", f"设备信息: {info}")
except Exception as e:
    log("U2", f"连接失败: {e}")

# ============ 4. 剪贴板测试 ============
print("\n" + "=" * 60)
print("剪贴板读取测试")
print("=" * 60)

log("剪贴板", "请在 10 秒内，在模拟器上手动复制任意一段文字（例如：在微信或浏览器里长按复制）")
print("倒计时 10 秒...")
for i in range(10, 0, -1):
    print(f"  {i}...", end='\r')
    time.sleep(1)
print()

if adb_device:
    try:
        output = adb_device.shell('dumpsys clipboard')
        log("剪贴板", f"dumpsys clipboard 输出长度: {len(output)}")
        log("剪贴板", f"输出前 1000 字符:\n{output[:1000]}")

        # 保存完整输出
        clip_file = os.path.join(LOG_DIR, f'diagnose_clipboard_{TS}.txt')
        with open(clip_file, 'w', encoding='utf-8') as f:
            f.write(output)
        log("剪贴板", f"完整输出已保存: {clip_file}")
    except Exception as e:
        log("剪贴板", f"读取剪贴板失败: {e}")
else:
    log("剪贴板", "ADB 设备未连接，跳过剪贴板测试")

# ============ 5. 拼多多搜索页 XML  dump ============
print("\n" + "=" * 60)
print("拼多多搜索页 XML 采集")
print("=" * 60)

if u2_device:
    try:
        from core.scraper import perform_search, extract_all_text_with_positions, parse_product_cards
        log("PDD", "尝试执行搜索...")
        if perform_search(u2_device, config.search_keyword):
            log("PDD", "搜索成功")

            # Dump XML
            xml = u2_device.dump_hierarchy()
            xml_file = os.path.join(LOG_DIR, f'diagnose_search_xml_{TS}.xml')
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(xml)
            log("PDD", f"搜索页 XML 已保存: {xml_file}")

            # 解析商品卡片
            items = extract_all_text_with_positions(u2_device)
            cards = parse_product_cards(items)
            log("PDD", f"解析到商品卡片: {len(cards)} 个")
            for i, card in enumerate(cards[:10]):
                log("PDD", f"  [{i+1}] 名称: {card.get('name', '')[:50]}")
                log("PDD", f"      desc: {card.get('desc', '')[:80]}")
                log("PDD", f"      店铺: {card.get('shop_name', '')}")
                log("PDD", f"      价格: {card.get('price_text', '')} 销量: {card.get('sales_text', '')}")

            # 保存解析结果
            parse_file = os.path.join(LOG_DIR, f'diagnose_parse_{TS}.txt')
            with open(parse_file, 'w', encoding='utf-8') as f:
                for i, card in enumerate(cards):
                    f.write(f"[{i+1}]\n")
                    f.write(f"  name: {card.get('name', '')}\n")
                    f.write(f"  desc: {card.get('desc', '')}\n")
                    f.write(f"  shop: {card.get('shop_name', '')}\n")
                    f.write(f"  price: {card.get('price_text', '')}\n")
                    f.write(f"  sales: {card.get('sales_text', '')}\n\n")
            log("PDD", f"解析结果已保存: {parse_file}")
        else:
            log("PDD", "搜索失败")
    except Exception as e:
        log("PDD", f"搜索/解析异常: {e}")
        import traceback
        log("PDD", traceback.format_exc())
else:
    log("PDD", "uiautomator2 未连接，跳过搜索页采集")

# ============ 6. 拼多多真实链接测试 ============
print("\n" + "=" * 60)
print("真实商品链接提取测试")
print("=" * 60)

if u2_device and cards:
    try:
        from core.link_extractor import extract_product_link
        log("链接", "点击第一个商品卡片进入详情页...")
        u2_device.click(224, 500)
        time.sleep(4)

        log("链接", "尝试提取真实链接...")
        link = extract_product_link(u2_device)
        log("链接", f"提取结果: {link[:100] if link else '空'}")

        link_file = os.path.join(LOG_DIR, f'diagnose_link_{TS}.txt')
        with open(link_file, 'w', encoding='utf-8') as f:
            f.write(f"提取到的链接: {link}\n")
        log("链接", f"结果已保存: {link_file}")
    except Exception as e:
        log("链接", f"链接提取异常: {e}")
        import traceback
        log("链接", traceback.format_exc())
else:
    log("链接", "跳过链接测试")

print("\n" + "=" * 60)
print("诊断完成")
print(f"请把 {LOG_DIR} 目录下 diagnose_*.txt / *.xml 文件发给我")
print("=" * 60)
