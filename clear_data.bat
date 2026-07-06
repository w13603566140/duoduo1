@echo off
chcp 65001 > nul
cd /d c:\Users\Administrator\Desktop\duoduo1

echo === 正在清空拼多多监控系统数据 ===
echo.

python clear_all_data.py

echo.
echo === 完成 ===
pause
