@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\Precision 7510\Desktop\Projects\mixed\dusun-eval"
"C:\Users\Precision 7510\AppData\Local\Programs\Python\Python313\python.exe" resume_pow_supervisor.py >> resume_pow_boot.log 2>&1
