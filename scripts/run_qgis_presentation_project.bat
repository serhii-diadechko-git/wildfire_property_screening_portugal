@echo off
setlocal
set "QGIS_ROOT=C:\Program Files\QGIS 3.44.12"
if "%~1"=="" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0build_qgis_presentation_assets.py"
  if errorlevel 1 exit /b %errorlevel%
)
call "%QGIS_ROOT%\bin\o4w_env.bat"
set "PATH=%QGIS_ROOT%\apps\qgis-ltr\bin;%QGIS_ROOT%\bin;%QGIS_ROOT%\apps\Python312;%QGIS_ROOT%\apps\Python312\DLLs;%PATH%"
set "QGIS_PREFIX_PATH=%QGIS_ROOT%\apps\qgis-ltr"
set "PYTHONPATH=%QGIS_ROOT%\apps\qgis-ltr\python"
set "QT_PLUGIN_PATH=%QGIS_ROOT%\apps\qgis-ltr\qtplugins;%QGIS_ROOT%\apps\qt5\plugins"
set "QT_QPA_PLATFORM=offscreen"
if "%~1"=="" (
  set "QGIS_SCRIPT=%~dp0build_qgis_presentation_project.py"
) else (
  set "QGIS_SCRIPT=%~f1"
)
"%QGIS_ROOT%\apps\Python312\python.exe" "%QGIS_SCRIPT%"
endlocal
