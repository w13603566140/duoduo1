@echo off
chcp 65001 >nul
title 拼多多销量采集监控 - 安装向导

echo ============================================
echo   拼多多商品销量采集监控系统 - 安装向导
echo ============================================
echo.

:: 检查Python
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] 未找到Python！请先安装Python 3.9+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   [OK] Python已安装

:: 检查ADB
echo [2/5] 检查ADB...
adb --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [WARN] 未找到ADB，将尝试使用uiautomator2内置ADB
    echo   如需手动安装: https://developer.android.com/tools/releases/platform-tools
) else (
    echo   [OK] ADB已安装
)

:: 创建虚拟环境
echo [3/5] 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo   [OK] 虚拟环境已创建
) else (
    echo   [OK] 虚拟环境已存在
)

:: 安装依赖
echo [4/5] 安装Python依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo   [WARN] 清华源安装失败，尝试默认源...
    pip install -r requirements.txt
)
echo   [OK] 依赖安装完成

:: 初始化数据库
echo [5/5] 初始化数据库...
python -c "from core.db import init_db; init_db(); print('数据库初始化完成')"
echo   [OK] 数据库已初始化

:: 创建.env配置
if not exist ".env" (
    echo   创建.env配置文件...
    copy .env.example .env >nul
    echo   [OK] .env文件已创建，请根据需要修改配置
)

echo.
echo ============================================
echo   安装完成！
echo ============================================
echo.
echo   使用方法:
echo     venv\Scripts\activate
echo     python main.py                  # 启动Web看板
echo     python main.py --run-once       # 执行一次采集
echo     python main.py --register-task  # 注册Windows定时任务
echo.
echo   Web看板: http://localhost:5000
echo.
pause
