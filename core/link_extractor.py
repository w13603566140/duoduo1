"""
从拼多多详情页提取商品链接（分享→复制链接→ADB读取剪贴板）
"""
import time
import re
import uiautomator2 as u2
import adbutils
from utils.logger import logger


def _get_device_serial(device: u2.Device) -> str:
    """从u2设备对象或配置中获取序列号"""
    # 尝试从设备对象获取
    serial = getattr(device, 'serial', None) or getattr(device, '_serial', None)
    if serial:
        return serial
    # 回退到配置
    from config import config
    return config.device_serial or '127.0.0.1:5555'


def get_clipboard_url(device_serial: str = None, max_attempts: int = 3) -> str:
    """
    通过ADB dumpsys clipboard读取剪贴板中的拼多多商品链接。
    失败返回空字符串。
    """
    candidates = []
    if device_serial:
        candidates.append(device_serial)

    # 常见模拟器/设备别名
    candidates.extend(['127.0.0.1:5555', 'emulator-5554', 'localhost:5555'])

    # 自动发现已连接设备
    try:
        client = adbutils.AdbClient()
        for d in client.device_list():
            if d.serial not in candidates:
                candidates.append(d.serial)
    except Exception as e:
        logger.warning('  ADB设备发现失败: {}'.format(e))

    # 去重
    seen = set()
    serials = []
    for s in candidates:
        if s and s not in seen:
            seen.add(s)
            serials.append(s)

    logger.debug('  尝试连接的设备: {}'.format(serials))

    goods_url_pattern = re.compile(
        r'https?://[^\s"<>]+yangkeduo\.com[^\s"<>]*goods[^\s"<>]*',
        re.IGNORECASE
    )
    generic_url_pattern = re.compile(
        r'https?://[^\s"<>]+yangkeduo\.com[^\s"<>]*',
        re.IGNORECASE
    )

    last_error = ''
    for attempt in range(1, max_attempts + 1):
        for serial in serials:
            try:
                client = adbutils.AdbClient()
                device = client.device(serial)
                output = device.shell('dumpsys clipboard')
                logger.debug('  [{}] 剪贴板 dumpsys 输出:\n{}'.format(serial, output[:800]))

                # 检查是否被 Android 15 红码
                if '<REDACTED>' in output or 'REDACTED' in output:
                    logger.warning('  剪贴板内容被系统隐藏 (REDACTED)，无法通过 ADB 读取')

                # 优先匹配 goods 链接
                for line in output.splitlines():
                    line = line.strip()
                    match = goods_url_pattern.search(line)
                    if match:
                        url = match.group(0)
                        logger.info('  从剪贴板获取链接: {}'.format(url[:60]))
                        return url[:1024]

                # 兜底匹配
                for line in output.splitlines():
                    match = generic_url_pattern.search(line)
                    if match:
                        url = match.group(0)
                        logger.info('  从剪贴板获取链接: {}'.format(url[:60]))
                        return url[:1024]

            except Exception as e:
                last_error = str(e)
                logger.debug('  ADB读取剪贴板失败 (attempt {}/{}, serial={}): {}'.format(
                    attempt, max_attempts, serial, e))

        logger.warning('  剪贴板中未找到有效链接 (attempt {}/{})'.format(attempt, max_attempts))
        if attempt < max_attempts:
            time.sleep(0.5)

    logger.warning('  无法从剪贴板读取链接: {}'.format(last_error))
    return ''


def extract_product_link(device: u2.Device) -> str:
    """
    在商品详情页上：点击分享→复制链接→ADB读取剪贴板。
    返回商品链接URL，失败返回空字符串。
    """
    try:
        serial = _get_device_serial(device)

        # 1. 点击分享按钮 (右上角: x≈858, y≈56)
        device.click(858, 56)
        time.sleep(2)

        # 2. 点击"复制链接" (bounds: [146,1303][226,1327], center: 186, 1315)
        device.click(186, 1315)
        time.sleep(1.5)

        # 3. 通过ADB直接读取剪贴板（无需粘贴到搜索框）
        link = get_clipboard_url(serial)

        # 4. 关闭分享弹窗
        device.press('back')
        time.sleep(0.5)

        # 5. 返回搜索结果页
        device.press('back')
        time.sleep(1.5)

        if link and 'yangkeduo' in link:
            return link[:1024]

        logger.warning('  未获取到有效商品链接')
        return ''

    except Exception as e:
        logger.warning('提取链接失败: {}'.format(e))
        try:
            device.screenshot('logs/link_extract_error.png')
        except:
            pass
        return ''
