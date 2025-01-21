@echo off
setlocal enabledelayedexpansion

:: 设置标题
title Free Transform Plugin Installer

:: 尝试多个可能的Python路径
set "POSSIBLE_PATHS=..\..\..\python_embeded\python.exe;..\..\python_embeded\python.exe;..\python_embeded\python.exe;python_embeded\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\..\python\python.exe;..\..\..\Python\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\..\python310\python.exe;..\..\..\Python310\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\..\python311\python.exe;..\..\..\Python311\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\..\python312\python.exe;..\..\..\Python312\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\python\python.exe;..\..\Python\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\python310\python.exe;..\..\Python310\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\python311\python.exe;..\..\Python311\python.exe"
set "POSSIBLE_PATHS=%POSSIBLE_PATHS%;..\..\python312\python.exe;..\..\Python312\python.exe"

:: 初始化Python路径为空
set "PYTHON_PATH="

echo Searching for Python...

:: 首先检查是否存在配置文件
if exist "python_path.txt" (
    set /p PYTHON_PATH=<python_path.txt
    if exist "!PYTHON_PATH!" (
        echo Found saved Python path: !PYTHON_PATH!
        goto :found_python
    )
)

:: 遍历可能的路径
for %%p in (%POSSIBLE_PATHS%) do (
    if exist "%%p" (
        set "PYTHON_PATH=%%p"
        echo Found Python at: %%p
        goto :check_version
    )
)

:: 如果没找到，让用户手动输入路径
:not_found
echo Python not found in default locations.
echo Please enter the path to your ComfyUI's python.exe:
echo Example: D:\ComfyUI\python_embeded\python.exe
set /p PYTHON_PATH="Path: "

:: 检查用户输入的路径是否存在
if not exist "%PYTHON_PATH%" (
    echo Error: Invalid path. Python not found at: %PYTHON_PATH%
    echo Would you like to try again? (Y/N)
    choice /c yn /n
    if errorlevel 2 goto :exit
    if errorlevel 1 goto :not_found
)

:check_version
:: 检查Python版本
"%PYTHON_PATH%" -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: Python version might be too old.
    echo Recommended: Python 3.10 or newer
    echo Current Python path: %PYTHON_PATH%
    echo Would you like to continue anyway? (Y/N)
    choice /c yn /n
    if errorlevel 2 goto :not_found
)

:found_python
echo Found Python at: %PYTHON_PATH%
echo.
echo Installing required packages...

:: 定义要安装的包列表
set "PACKAGES=addict blend-modes segment-anything pyqt5 yapf platformdirs translate pycryptodome pycryptodomex"

:: 检查pip是否可用
"%PYTHON_PATH%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: pip not found. Attempting to install pip...
    "%PYTHON_PATH%" -m ensurepip --default-pip
    if !errorlevel! neq 0 (
        echo Failed to install pip. Please install pip manually.
        goto :exit
    )
)

:: 升级pip
echo Upgrading pip...
"%PYTHON_PATH%" -m pip install --upgrade pip

:: 安装所有依赖
for %%p in (%PACKAGES%) do (
    echo Installing %%p...
    "%PYTHON_PATH%" -m pip install --user %%p
    if !errorlevel! neq 0 (
        echo Warning: Failed to install %%p, will try with admin rights later.
    )
)

:: 检查关键包是否安装成功
"%PYTHON_PATH%" -c "from Cryptodome.Cipher import AES; import addict; from blend_modes import normal" >nul 2>&1
if %errorlevel% equ 0 (
    echo All dependencies installed successfully!
) else (
    echo Some packages failed to install, attempting with administrator privileges...
    
    :: 创建临时的提升权限脚本
    echo @echo off > "%temp%\elevate.bat"
    echo "%PYTHON_PATH%" -m pip install --upgrade pip >> "%temp%\elevate.bat"
    for %%p in (%PACKAGES%) do (
        echo "%PYTHON_PATH%" -m pip install --user %%p >> "%temp%\elevate.bat"
    )
    
    :: 使用 PowerShell 提升权限运行
    powershell -Command "Start-Process '%temp%\elevate.bat' -Verb RunAs -Wait"
    
    :: 再次检查安装
    "%PYTHON_PATH%" -c "from Cryptodome.Cipher import AES; import addict; from blend_modes import normal" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Dependencies installed successfully with admin rights!
    ) else (
        echo Error: Some installations failed even with admin rights.
        echo Please try installing manually using:
        echo pip install addict blend-modes segment-anything pyqt5 yapf platformdirs translate pycryptodome pycryptodomex
    )
)

:: 保存成功的Python路径到配置文件
if %errorlevel% equ 0 (
    echo %PYTHON_PATH%> python_path.txt
    echo Python path saved for future use.
)

:: 清理临时文件
if exist "%temp%\elevate.bat" del "%temp%\elevate.bat"

:exit
echo.
echo Installation process completed!
echo You can now close this window.
pause 