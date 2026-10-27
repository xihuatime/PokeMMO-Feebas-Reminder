@echo off
rem ============================================================
rem  丑丑鱼点刷新提醒工具 - 本地一键打包脚本（双击即可运行）
rem  产物输出到 dist\ 目录，方便本地测试
rem  打包参数与 GitHub Actions 保持一致，两边产物完全一样
rem ============================================================
setlocal
cd /d "%~dp0"

echo ============================================
echo   丑丑鱼点刷新提醒工具 - 本地打包
echo ============================================
echo.

rem ---------- 1. 检查 Python ----------
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python 命令。
    echo        请安装 Python 3.8 或更高版本，安装时勾选 "Add Python to PATH"。
    pause
    exit /b 1
)

rem ---------- 2. 检查 tkinter ----------
rem  没有 tkinter 打出来的 exe 会缺弹窗，这里提前拦住，别等到运行才发现
echo [2/4] 检查 tkinter 组件...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [错误] 当前 Python 缺少 tkinter，打出的 exe 会没有主界面。
    echo        修复：重新运行 Python 安装包 -^> Modify -^> 勾选 "tcl/tk and IDLE" -^> Install。
    pause
    exit /b 1
)

rem ---------- 3. 安装依赖 ----------
echo [3/4] 安装依赖...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [错误] 依赖安装失败。网络慢可以换国内镜像重试：
    echo        python -m pip install -r requirements.txt pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)

rem ---------- 4. 打包 ----------
rem  固定参数：--onefile 单文件 / --windowed 无控制台黑框 / --name 产物名 / --icon exe 图标
echo [4/4] 开始打包，约需 1-2 分钟...
python -m PyInstaller --onefile --windowed --name "丑丑鱼点刷新提醒工具" --icon "icon.ico" reminder.py
if errorlevel 1 (
    echo [错误] 打包失败，请查看上方 PyInstaller 的报错信息。
    pause
    exit /b 1
)

echo.
echo ============================================
echo   打包完成：dist\丑丑鱼点刷新提醒工具.exe
echo   双击该 exe 即可运行，目标机器无需 Python
echo ============================================
pause
