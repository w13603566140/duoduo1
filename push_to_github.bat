@echo off
chcp 65001 > nul
cd /d c:\Users\Administrator\Desktop\duoduo1

echo === GitHub 提交脚本 ===
echo.

echo [1/4] 检查远程仓库...
git remote -v

echo.
echo [2/4] 检查本地状态...
git status --short

echo.
echo [3/4] 检查 GitHub 认证...
gh auth status

echo.
echo [4/4] 推送到 GitHub...
git push -u origin main

echo.
echo === 完成 ===
pause
