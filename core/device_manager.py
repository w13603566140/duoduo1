"""
设备管理器 - ADB连接、设备健康检查、重连、拼多多APP管理
"""
import time
import uiautomator2 as u2

from config import config
from utils.logger import logger
from utils.helpers import retry


class DeviceManager:
    """管理Android设备连接和拼多多APP生命周期"""

    def __init__(self, serial: str = None):
        self.serial = serial or config.device_serial
        self.device = None

    def connect(self) -> u2.Device:
        """
        连接到设备。
        支持USB直连、IP无线连接、模拟器ADB端口。
        """
        if self.serial:
            logger.info(f"连接到设备: {self.serial}")
            self.device = u2.connect(self.serial)
        else:
            logger.info("自动检测USB设备...")
            self.device = u2.connect_usb()

        logger.info(f"设备连接成功: {self.device.info}")
        return self.device

    @retry(max_attempts=3, delay=3.0)
    def ensure_device_ready(self) -> u2.Device:
        """
        确保设备就绪：连接、唤醒屏幕、检查APP已安装。
        带重试机制。
        """
        if self.device is None:
            self.connect()

        # 获取设备信息以确认连接
        info = self.device.info
        logger.info(f"设备型号: {info.get('productName', 'Unknown')}, "
                     f"SDK: {info.get('sdkInt', 'Unknown')}")

        # 唤醒屏幕
        try:
            self.device.screen_on()
            logger.info("屏幕已唤醒")
        except Exception:
            pass  # 屏幕可能已经是亮的

        # 检查拼多多是否已安装
        pdd_package = config.pdd_package
        app_info = self.device.app_info(pdd_package)
        if app_info:
            logger.info(f"拼多多已安装: version={app_info.get('versionName', 'unknown')}")
        else:
            logger.warning("拼多多未安装！请在手机上安装拼多多APP")

        return self.device

    def launch_app(self):
        """启动拼多多APP"""
        logger.info("启动拼多多APP...")
        self.device.app_start(config.pdd_package)
        time.sleep(3)  # 等待APP启动

    def stop_app(self):
        """强制停止拼多多APP"""
        logger.info("停止拼多多APP...")
        try:
            self.device.app_stop(config.pdd_package)
        except Exception as e:
            logger.warning(f"停止APP失败: {e}")
        time.sleep(1)

    def is_app_running(self) -> bool:
        """检查拼多多是否在前台运行"""
        try:
            current = self.device.app_current()
            package = current.get("package", "")
            return config.pdd_package in package
        except Exception:
            return False

    def dismiss_popups(self):
        """
        尝试关闭各种弹窗（广告、更新提示、红包等）。
        非致命——如果没有弹窗，静默继续。
        """
        dismiss_patterns = [
            # 按文本匹配
            (self.device(text="跳过"), "跳过按钮"),
            (self.device(text="关闭"), "关闭按钮"),
            (self.device(text="取消"), "取消按钮"),
            (self.device(text="我知道了"), "我知道了按钮"),
            (self.device(text="以后再说"), "以后再说"),
            # 按resource-id匹配（拼多多常见ID）
            (self.device(resourceId="com.xunmeng.pinduoduo:id/iv_close"), "关闭图标(id)"),
            (self.device(resourceId="com.xunmeng.pinduoduo:id/btn_close"), "关闭按钮(id)"),
            (self.device(resourceId="com.xunmeng.pinduoduo:id/close_btn"), "关闭按钮2(id)"),
            (self.device(resourceId="com.xunmeng.pinduoduo:id/tv_skip"), "跳过(id)"),
            (self.device(resourceId="com.xunmeng.pinduoduo:id/dialog_close"), "弹窗关闭(id)"),
            # 按className + description匹配
            (self.device(className="android.widget.ImageView", description="关闭"), "关闭图标(desc)"),
        ]

        for element, desc in dismiss_patterns:
            try:
                if element.exists(timeout=0.5):
                    element.click()
                    logger.info(f"  关闭弹窗: {desc}")
                    time.sleep(0.5)
            except Exception:
                pass

        # 也尝试按返回键关闭可能的弹窗
        try:
            # 检查常见的弹窗包名
            current = self.device.app_current()
            if current.get("package") != config.pdd_package:
                self.device.press("back")
        except Exception:
            pass

    def close(self):
        """释放设备连接"""
        logger.info("释放设备连接")
        self.device = None


# 全局设备管理器实例
device_manager = DeviceManager()
