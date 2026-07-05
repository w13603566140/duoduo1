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
    if not device_serial:
        device_serial = '127.0.0.1:5555'

    # 优先匹配包含 goods_id 的真实商品链接
    goods_url_pattern = re.compile(
        r'https?://[^\s"<>]+yangkeduo\.com[^\s"<>]*goods[^\s"<>]*',
        re.IGNORECASE
    )
    # 兜底：匹配任意拼多多域名链接
    generic_url_pattern = re.compile(
        r'https?://[^\s"<>]+yangkeduo\.com[^\s"<>]*',
        re.IGNORECASE
    )

    for attempt in range(1, max_attempts + 1):
        try:
            client = adbutils.AdbClient()
            device = client.device(device_serial)
            output = device.shell('dumpsys clipboard')
            logger.debug('剪贴板 dumpsys 输出:\n{}'.format(output[:500]))

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

            logger.warning('  剪贴板中未找到有效链接 (attempt {}/{})'.format(attempt, max_attempts))
            if attempt < max_attempts:
                time.sleep(0.5)

        except Exception as e:
            logger.warning('  ADB读取剪贴板失败 (attempt {}/{}): {}'.format(attempt, max_attempts, e))
            if attempt < max_attempts:
                time.sleep(0.5)

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
