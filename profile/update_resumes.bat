@echo off
echo ================================================
echo   Resume PDF Extractor
echo   Extracts base resume PDFs to markdown files
echo ================================================
echo.
echo Looking for PDF files in this folder...
echo.

cd /d "%~dp0.."
python scripts\extract_resume_pdf.py

echo.
echo ================================================
echo   Done! Check profile\ for updated .md files.
echo ================================================
echo.
pause
