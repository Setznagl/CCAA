@echo off
setlocal
powershell.exe -NoProfile -File "%~dp0executar.ps1"
set "resultado=%ERRORLEVEL%"
if not "%resultado%"=="0" (
  echo.
  echo O lote terminou com erro. Confira a mensagem acima.
  echo Se houver bloqueio de politica ou permissao, procure o suporte de TI.
  echo Nenhuma politica do Windows foi alterada. Consulte LEIA-ME.txt.
  pause
)
exit /b %resultado%
