# طيبه (Taybah) — Nutrition & Clinic System

Clinic nutrition platform branded **طيبه**: patient diary/macros, subscription meals, plus clinic revenue billing and physician nutrition plans.

A full-stack nutrition tracking application (similar to MyFitnessPal or Cronometer) for logging daily meals, tracking macronutrients, and comparing intake against personal targets — extended with clinic staff workflows from the revenue and clinical nutrition specifications.


---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Django 6, Django REST Framework, SimpleJWT, SQLite (dev) |
| **Frontend** | React 19 (Vite), Tailwind CSS 4, Axios, Recharts |
| **External API** | [Open Food Facts](https://world.openfoodfacts.org/) (food search fallback) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (:5173)                  │
│  Dashboard · DiaryContext · FoodSearch · Macro Charts       │
└───────────────────────────┬─────────────────────────────────┘
                            │ /api/* (JWT)
┌───────────────────────────▼─────────────────────────────────┐
│                     Django Backend (:8000)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ apps/foods  │  │ apps/diary  │  │ apps/accounts       │  │
│  │ FoodItem    │  │ DailyDiary  │  │ UserProfile         │  │
│  │ (master DB) │  │ MealLog     │  │ (targets, TDEE)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ (cache miss)
                            ▼
                   Open Food Facts API
```

**Core rules**

1. **Master Food Database** (`FoodItem`) — read-only for users; admin-managed + auto-cached from Open Food Facts.
2. **User Daily Diary** (`DailyDiary`, `MealLog`) — transactional per-user meal logs.
3. **Backend calculates totals** — TDEE, daily macro sums; frontend displays only.

---

## Project Structure

```
nutrition-tracker/
├── backend/
│   ├── apps/
│   │   ├── accounts/     # UserProfile (OneToOne with Django User)
│   │   ├── foods/        # FoodItem master DB + search service
│   │   └── diary/        # DailyDiary, MealLog, today summary
│   ├── config/           # Django settings, root URLs
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # axios, diary, foods API clients
│   │   ├── context/      # DiaryContext (state management)
│   │   ├── components/   # charts, diary, foods UI
│   │   └── pages/        # Dashboard
│   └── vite.config.js
└── README.md
```

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Git** (optional)

---

## First-Time Setup

### 1. Clone or navigate to the project

```powershell
cd C:\Users\Sabri\Projects\nutrition-tracker
```

### 2. Backend setup

```powershell
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create database tables
python manage.py migrate

# Create a superuser (follow prompts)
python manage.py createsuperuser
```

> **PowerShell note:** If script activation is blocked, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 3. Frontend setup

```powershell
cd ..\frontend
npm install
```

---

## Running the Application

You need **two terminals** running at the same time.

### Terminal 1 — Backend (port 8000)

```powershell
cd C:\Users\Sabri\Projects\nutrition-tracker\backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

- API base: http://localhost:8000/api/
- Admin panel: http://localhost:8000/admin/

### Terminal 2 — Frontend (port 5173)

```powershell
cd C:\Users\Sabri\Projects\nutrition-tracker\frontend
npm run dev
```

- App URL: http://localhost:5173

The Vite dev server proxies `/api` requests to Django automatically (see `frontend/vite.config.js`).

---

## Authentication

All API endpoints require JWT authentication.

### Get tokens

```powershell
curl -X POST http://localhost:8000/api/auth/token/ `
  -H "Content-Type: application/json" `
  -d "{\"username\": \"YOUR_USERNAME\", \"password\": \"YOUR_PASSWORD\"}"
```

Response:

```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

### Store tokens in the browser

Open http://localhost:5173, open DevTools → Console, and run:

```javascript
localStorage.setItem('access_token', 'YOUR_ACCESS_TOKEN')
localStorage.setItem('refresh_token', 'YOUR_REFRESH_TOKEN')
location.reload()
```

The Axios client (`frontend/src/api/axios.js`) attaches the access token to every request and automatically refreshes it on `401` responses.

---

## User Profile Setup

The dashboard summary requires a `UserProfile` linked to your user. Without it, you'll see: *"Complete your profile to view daily targets."*

### Option A — Django Admin

1. Go to http://localhost:8000/admin/
2. Log in with your superuser credentials
3. Create a **User Profile** linked to your user

### Option B — Django Shell

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py shell
```

```python
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile

user = User.objects.get(username="YOUR_USERNAME")

UserProfile.objects.get_or_create(
    user=user,
    defaults={
        "weight_kg": 75,
        "height_cm": 175,
        "age": 30,
        "gender": "male",           # male | female | other
        "activity_level": "moderately_active",
        "target_calories": 2500,
        "target_protein": 150,
        "target_carbs": 250,
        "target_fats": 80,
    },
)
```

### Activity levels

| Value | Description |
|-------|-------------|
| `sedentary` | Little or no exercise |
| `lightly_active` | 1–3 days/week |
| `moderately_active` | 3–5 days/week |
| `very_active` | 6–7 days/week |
| `extra_active` | Physical job or 2× training |

TDEE is calculated server-side using the **Mifflin-St Jeor** equation (`apps/accounts/services/tdee.py`).

---

## Seed Sample Foods (Optional)

```powershell
python manage.py shell
```

```python
from decimal import Decimal
from apps.foods.models import FoodItem

FoodItem.objects.get_or_create(
    name="Chicken Breast",
    defaults={
        "calories": Decimal("165"),
        "protein": Decimal("31"),
        "carbs": Decimal("0"),
        "fats": Decimal("3.6"),
        "fiber": Decimal("0"),
        "serving_size": Decimal("100"),
        "serving_unit": "g",
    },
)
```

If local search finds no matches, the backend queries **Open Food Facts**, caches results in `FoodItem`, and returns them on subsequent searches.

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/token/` | Obtain access + refresh tokens |
| `POST` | `/api/auth/token/refresh/` | Refresh access token |

### Diary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/diary/` | List user's daily diaries |
| `POST` | `/api/diary/` | Create a diary entry `{ "date": "2026-07-11" }` |
| `GET` | `/api/diary/{id}/` | Get diary with nested meal logs |
| `GET` | `/api/diary/today/summary/` | Today's consumed vs target macros |
| `GET` | `/api/meal-logs/` | List meal logs (`?daily_diary=1&meal_type=breakfast`) |
| `POST` | `/api/meal-logs/` | Log food `{ "daily_diary", "meal_type", "food_item_id", "quantity" }` |
| `DELETE` | `/api/meal-logs/{id}/` | Remove a meal log |

### Foods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/foods/search/?search_terms=chicken` | Search local DB; fallback to Open Food Facts |
| `GET` | `/api/foods/` | Browse cached food items |
| `GET` | `/api/foods/{id}/` | Food item detail |

### Today summary response

```json
{
  "date": "2026-07-11",
  "consumed": { "calories": 330.0, "protein": 62.0, "carbs": 0.0, "fats": 7.2 },
  "targets":  { "calories": 2500, "protein": 150, "carbs": 250, "fats": 80 },
  "remaining": { "calories": 2170.0, "protein": 88.0, "carbs": 250.0, "fats": 72.8 }
}
```

### Food search response

```json
{
  "search_terms": "nutella",
  "source": "openfoodfacts",
  "count": 5,
  "results": [
    {
      "id": 12,
      "name": "Nutella",
      "brand": "Ferrero",
      "calories": "80.00",
      "protein": "0.90",
      "carbs": "8.60",
      "fats": "4.60",
      "serving_size": "15.00",
      "serving_unit": "g"
    }
  ]
}
```

---

## Using the Dashboard

1. **Open** http://localhost:5173 (with JWT tokens in `localStorage`).
2. **View** today's calorie ring and macro progress bars (Recharts).
3. **Browse meals** — Breakfast, Lunch, Dinner, Snacks.
4. **Add food** — Click **+ Add Food** on any meal section.
5. **Search** — Type at least 2 characters; results debounce at 350ms.
6. **Select food** — Choose a result, enter quantity/servings, confirm.
7. **Remove** — Click **Remove** on any logged item.

State is managed by `DiaryContext`: summary and meal logs load once on mount; add/remove updates local state without re-fetching the summary endpoint.

---

## Running Tests

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py test
```

Food search tests only:

```powershell
python manage.py test apps.foods.tests.test_search
```

### Frontend build

```powershell
cd frontend
npm run build
```

---

## Production Build (Frontend)

```powershell
cd frontend
npm run build
npm run preview   # preview production build at http://localhost:4173
```

Built files are output to `frontend/dist/`.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `401 Unauthorized` | Set `access_token` and `refresh_token` in `localStorage` |
| `Complete your profile` | Create a `UserProfile` for your user (see above) |
| PowerShell won't activate venv | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Port 8000 in use | `python manage.py runserver 8001` and update Vite proxy |
| Port 5173 in use | Change `server.port` in `frontend/vite.config.js` |
| Food search returns empty | Check internet access (Open Food Facts fallback); try 2+ characters |
| CORS errors | Ensure frontend runs on `localhost:5173` (allowed in `config/settings.py`) |

---

## Environment Variables (Optional)

For PostgreSQL or production, create `backend/.env`:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DB_NAME=nutrition_tracker
DB_USER=nutrition_user
DB_PASSWORD=nutrition_pass
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Default development uses **SQLite** (`backend/db.sqlite3`) with no `.env` required.

---

## License

Private / educational project. Open Food Facts data is subject to the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1.0/).
