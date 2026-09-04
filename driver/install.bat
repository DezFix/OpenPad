@echo off
REM === OpenPad Virtual Mic — установка драйвера (черновик, WIP) ===
REM Требует: собранный подписанный пакет драйвера (driver\package\).
REM Запускать от администратора. После установки нужна перезагрузка,
REM если ставится первый раз.
setlocal
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [OpenPad] Запустите от имени администратора.
  exit /b 1
)
if not exist "%~dp0package\OpenPadCable.inf" (
  echo [OpenPad] Пакет драйвера не собран: driver\package\OpenPadCable.inf нет.
  echo [OpenPad] См. driver\TODO.md, шаг 1-3.
  exit /b 2
)
echo [OpenPad] Установка OpenPadCable...
pnputil /add-driver "%~dp0package\OpenPadCable.inf" /install
if %errorlevel% neq 0 (
  echo [OpenPad] Ошибка установки. Код: %errorlevel%
  exit /b 3
)
echo [OpenPad] Готово. Выберите в OpenPad: Вирт. микрофон = OpenPad Virtual Mic.
endlocal
