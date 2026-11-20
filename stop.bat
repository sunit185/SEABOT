@echo off
echo Stopping Seabot processes...
taskkill /F /FI "WINDOWTITLE eq Seabot Backend*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Seabot Frontend*" 2>nul
echo Seabot stopped.
