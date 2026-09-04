@echo off
REM === OpenPad Virtual Mic — удаление драйвера (черновик, WIP) ===
REM Запускать от администратора.
setlocal
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [OpenPad] Запустите от имени администратора.
  exit /b 1
)
echo [OpenPad] Поиск пакета oem*.inf с OpenPadCable...
for /f "tokens=*" %%f in ('pnputil /enum-drivers ^| findstr /i OpenPadCable') do (
  echo [OpenPad] Найдено: %%f
)
echo [OpenPad] Удалите пакет вручную: pnputil /delete-driver oemNN.inf /uninstall
echo [OpenPad] (номер возьмите из строки выше)
endlocal
