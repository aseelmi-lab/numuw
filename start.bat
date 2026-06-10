@echo off
chcp 65001 >nul
echo ========================================
echo        تشغيل تطبيق نمو
echo ========================================
echo.
echo جاري تثبيت المتطلبات...
pip install -r requirements.txt -q
echo.
echo جاري تشغيل السيرفر...
echo افتح المتصفح على: http://127.0.0.1:5000
echo.
py app.py
pause
