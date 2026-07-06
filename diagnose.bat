@echo off
chcp 65001 > nul
cd /d c:\Users\Administrator\Desktop\duoduo1

echo === 正在运行拼多多采集系统诊断 ===
echo.

python diagnose.py

echo.
echo === 诊断完成 ===
echo 请把 logs 目录下 diagnose_*.txt 和 *.xml 文件发给 Claude
pause
