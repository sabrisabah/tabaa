# عيادة دكتورة طيبة للتغذية

نظام متابعة المراجعين لعيادة تغذية — بثلاث واجهات: مريض، طبيب، سكرتيرة.

## التشغيل المحلي

```bash
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py seed_doctor
python manage.py runserver
```

ثم افتح:

- المريض: http://127.0.0.1:8000/
- الطبيب: http://127.0.0.1:8000/doctor/
- السكرتيرة: http://127.0.0.1:8000/secretary/
- لوحة Django: http://127.0.0.1:8000/admin/

### حساب الطبيب الافتراضي

- البريد: `doctor@taiba.clinic`
- كلمة المرور: `doctor123`

أنشئ حساب السكرتيرة من لوحة الإدارة (`Users` → role = secretary).

## التقنية

- Backend: Django 5.2 + DRF + Simple JWT + SQLite
- Frontend: HTML / CSS / JS (RTL)
- استيراد/تصدير Excel من Django Admin
- أرقام الملفات: `TAIBA-0001`, `TAIBA-0002`, ...

## متغيرات البيئة (الإنتاج)

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` (اختياري — PostgreSQL على Railway)
