"""
从拼多多详情页提取商品链接（分享→复制链接→粘贴读取）
"""
import time
import re
import uiautomator2 as u2
from utils.logger import logger


def extract_product_link(device: u2.Device) -> str:
    """
    在商品详情页上：点击分享→复制链接→返回→粘贴到搜索框读取。
    返回商品链接URL，失败返回空字符串。
    """
    try:
        # 1. 点击分享按钮 (右上角: x≈858, y≈56)
        device.click(858, 56)
        time.sleep(2)

        # 2. 点击"复制链接" (bounds: [146,1303][226,1327], center: 186, 1315)
        device.click(186, 1315)
        time.sleep(1.5)

        # 3. 关闭分享弹窗
        device.press('back')
        time.sleep(1)

        # 4. 返回搜索结果页
        device.press('back')
        time.sleep(2)

        # 5. 打开搜索栏
        device.click(400, 73)
        time.sleep(3)

        # 6. 找到搜索框，清空旧内容
        si = device(
            resourceId='com.xunmeng.pinduoduo:id/pdd',
            className='android.widget.EditText'
        )
        if not si.exists(timeout=3):
            return ''

        si.click()
        time.sleep(0.5)
        si.set_text('')
        time.sleep(0.3)

        # 7. 长按触发粘贴菜单
        device.long_click(450, 73)
        time.sleep(1)

        # 8. 查找并点击"粘贴"按钮
        xml = device.dump_hierarchy()
        for m in re.finditer(r'<node[^>]*>', xml):
            full = m.group()
            text = re.search(r'text="([^"]+)"', full)
            if text and ('粘贴' in text.group(1)):
                bounds = re.search(r'bounds="([^"]+)"', full)
                if bounds:
                    b = bounds.group(1)
                    parts = b.replace('][', ',').replace('[', '').replace(']', '').split(',')
                    cx = (int(parts[0]) + int(parts[2])) // 2
                    cy = (int(parts[1]) + int(parts[3])) // 2
                    device.click(cx, cy)
                    time.sleep(1)
                    break

        # 9. 读取粘贴的内容
        link = si.get_text() or ''
        if link and 'yangkeduo' in link:
            logger.info('  获取链接: {}'.format(link[:60]))
            return link[:1024]

        return ''

    except Exception as e:
        logger.warning('提取链接失败: {}'.format(e))
        return ''
