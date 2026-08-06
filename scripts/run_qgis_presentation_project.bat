@echo off
setlocal
rem Optional Windows helper. It never stores a user-specific QGIS location.
rem Set QGIS_ROOT once in your user environment, or let this script discover
rem the newest QGIS directory under Program Files.
if not defined QGIS_ROOT (
  for /d %%D in ("%ProgramFiles%\QGIS *") do set "QGIS_ROOT=%%~fD"
)
if not defined QGIS_ROOT (
  echo QGIS_ROOT is not set and QGIS was not found under Program Files.
  echo Set QGIS_ROOT to your QGIS installation directory, then run this script again.
  exit /b 1
)
if not exist "%QGIS_ROOT%\bin\o4w_env.bat" (
  echo QGIS_ROOT does not point to a valid QGIS installation: %QGIS_ROOT%
  exit /b 1
)
set "QGIS_ARGUMENTS="
if /I "%~1"=="--validate-existing" (
  set "QGIS_SCRIPT=%~dp0build_qgis_presentation_project.py"
  set "QGIS_ARGUMENTS=--validate-existing"
) else if "%~1"=="" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0build_qgis_presentation_assets.py"
  if errorlevel 1 exit /b %errorlevel%
  set "QGIS_SCRIPT=%~dp0build_qgis_presentation_project.py"
) else (
  set "QGIS_SCRIPT=%~f1"
)
call "%QGIS_ROOT%\bin\o4w_env.bat"
set "PATH=%QGIS_ROOT%\apps\qgis-ltr\bin;%QGIS_ROOT%\bin;%QGIS_ROOT%\apps\Python312;%QGIS_ROOT%\apps\Python312\DLLs;%PATH%"
set "QGIS_PREFIX_PATH=%QGIS_ROOT%\apps\qgis-ltr"
set "PYTHONPATH=%QGIS_ROOT%\apps\qgis-ltr\python"
set "QT_PLUGIN_PATH=%QGIS_ROOT%\apps\qgis-ltr\qtplugins;%QGIS_ROOT%\apps\qt5\plugins"
set "QT_QPA_PLATFORM=offscreen"
"%QGIS_ROOT%\apps\Python312\python.exe" "%QGIS_SCRIPT%" %QGIS_ARGUMENTS%
endlocal
