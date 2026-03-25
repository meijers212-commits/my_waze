# 🛒 My Waze — Smart Grocery Receipt Scanner

---

## עברית

### מה זה?

**My Waze** הוא אפליקציית ווב חכמה לניהול קניות מכולת.  
המשתמש מעלה תמונה של קבלה (או מצלם ישירות מהמצלמה), המערכת מחלצת את המוצרים אוטומטית בעזרת AI (Gemini של Google), ואז מאפשרת להשוות את סל הקניות בין סניפים שונים לפי מחיר.

---

### פיצ'רים עיקריים

| פיצ'ר | תיאור |
|---|---|
| **סריקת קבלה** | העלאת תמונה או צילום ישיר מהמצלמה |
| **OCR מבוסס AI** | חילוץ אוטומטי של מוצרים ומחירים מקבלות בעברית |
| **ניהול סל קניות** | הוספה, עריכה ומחיקה של מוצרים בסל |
| **השוואת מחירים** | השוואת הסל מול כל החנויות בבסיס הנתונים |
| **היסטוריית מחירים** | שמירת מחירי מוצרים לאורך זמן לפי חנות |
| **מוצרים פופולריים** | הצגת מוצרים נפוצים בדשבורד |
| **אימות משתמשים** | הרשמה, כניסה, JWT session מאובטח |

---

### ארכיטקטורה

האפליקציה מחולקת לשלושה שירותים עצמאיים:

```
┌─────────────────────────────────────────────────────┐
│                   דפדפן (React)                      │
│              Vite + React 19 + Tailwind              │
└────────────┬─────────────────────┬───────────────────┘
             │                     │
             ▼                     ▼
┌────────────────────┐   ┌─────────────────────────────┐
│  server_auth       │   │  backend_server              │
│  Node.js + Express │   │  Python + FastAPI            │
│  MongoDB           │   │  MySQL + Gemini AI           │
│  PORT: 5000        │   │  PORT: 8000                  │
└────────────────────┘   └─────────────────────────────┘
```

| שכבה | טכנולוגיה | אחריות |
|---|---|---|
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, React Router 7 | ממשק משתמש |
| **Auth Server** | Node.js, Express 4, MongoDB, JWT, bcryptjs | משתמשים, כניסה, סל קניות, מוצרים פופולריים |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, MySQL 8, Gemini AI | OCR קבלות, השוואת מחירים, קטלוג מוצרים |

---

### מבנה תיקיות

```
my_waze/
├── client/                        # פרונטאנד (React + Vite)
│   ├── src/
│   │   ├── Pages/                 # דפים: Auth, Dashboard, Cart, Scan, Details, Compare
│   │   ├── Comps/                 # קומפוננטות: Auth, Cart, Dashboard, Scan
│   │   ├── hooks/                 # Custom hooks: useAuth, useCart, useCompare, useCameraCapture
│   │   ├── Contexts/              # AuthContext
│   │   └── test/                  # setupTests.js
│   ├── .env.example
│   └── vite.config.js
│
├── server_auth/                   # שרת אימות (Node.js + Express)
│   ├── controllers/               # authController, cartController, productsController
│   ├── models/                    # User (MongoDB)
│   ├── routes/                    # auth, cart, products
│   ├── middleware/                # auth.js (JWT protect)
│   ├── db/                        # MongoDB client
│   └── .env.example
│
└── backend_server/                # שרת נתונים (Python + FastAPI)
    ├── app/
    │   ├── api/                   # receipt_routes, basket_routes, products_routes
    │   ├── services/              # OCRService, ReceiptService, BasketService
    │   ├── models/                # Product, Store, PriceHistory (SQLAlchemy)
    │   ├── schemas/               # Pydantic schemas
    │   └── core/                  # config, constants, enums
    ├── migrations/                # Alembic migrations
    ├── dockerfile
    ├── docker-compose.yml
    └── .env.example
```

---

### התקנה והרצה מקומית

#### דרישות מוקדמות

- Node.js 18+
- Python 3.11+
- MongoDB פועל מקומית (או Atlas)
- MySQL 8 פועל מקומית (או Docker)
- מפתח API של Google Gemini

---

#### 1. Frontend (client)

```bash
cd client
cp .env.example .env
# ערוך את .env לפי הצורך
npm install
npm run dev
```

פועל על: `http://localhost:5173`

**משתני env:**
```env
VITE_API_URL=http://localhost:5000/api        # שרת Auth
VITE_DATA_API_URL=http://localhost:8000       # שרת Backend
```

---

#### 2. Auth Server (server_auth)

```bash
cd server_auth
cp .env.example .env
# ערוך את .env לפי הצורך
npm install
node index.js
```

פועל על: `http://localhost:5000`

**משתני env:**
```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=my_waze
JWT_SECRET=your_jwt_secret
JWT_EXPIRES_IN=7d
PORT=5000
CLIENT_URL=http://localhost:5173
```

---

#### 3. Backend Server (backend_server)

**עם Docker (מומלץ):**
```bash
cd backend_server
docker-compose up -d       # מריץ MySQL בלבד
cp .env.example .env
# ערוך את .env עם GEMINI_API_KEY ו-SQLALCHEMY_DATABASE_URL
pip install -r requirements.txt
alembic upgrade head       # מריץ migrations
uvicorn app.main:app --reload --port 8000
```

**משתני env:**
```env
SQLALCHEMY_DATABASE_URL=mysql+pymysql://user:password@localhost:3306/grocery_app
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-1.5-flash
CORS_ALLOW_ORIGINS=http://localhost:5173
CREATE_TABLES_ON_STARTUP=false
```

פועל על: `http://localhost:8000`  
תיעוד API: `http://localhost:8000/docs`

---

### API Endpoints

#### Backend (FastAPI) — `http://localhost:8000`

| Method | Path | תיאור |
|---|---|---|
| `POST` | `/receipts/upload` | העלאת תמונת קבלה לחילוץ OCR |
| `POST` | `/basket/compare` | השוואת סל קניות בין חנויות |
| `GET` | `/products` | רשימת מוצרים עם חיפוש |

#### Auth Server (Express) — `http://localhost:5000/api`

| Method | Path | Auth | תיאור |
|---|---|---|---|
| `GET` | `/health` | ❌ | בדיקת זמינות |
| `POST` | `/auth/register` | ❌ | הרשמת משתמש |
| `POST` | `/auth/login` | ❌ | כניסה |
| `GET` | `/auth/me` | ✅ JWT | פרטי משתמש מחובר |
| `GET` | `/products` | ✅ JWT | רשימת מוצרים |
| `GET` | `/products/popular` | ✅ JWT | מוצרים פופולריים |
| `GET/POST/PATCH/DELETE` | `/cart` | ✅ JWT | ניהול סל קניות |
| `PUT` | `/cart/store` | ✅ JWT | עדכון חנות נבחרת |

---

### בדיקות

```bash
cd client
npm run test        # מריץ את כל הטסטים עם Vitest
npm run lint        # בדיקת ESLint
npm run build       # בדיקת build לפרודקשן
```

---

### Deploy

- **Frontend:** Render / Vercel / Netlify — `npm run build` ואז העלאת `dist/`
- **Backend (FastAPI):** Render / Railway — עם `dockerfile` מובנה
- **Auth Server:** Render / Railway — `node index.js`
- **MySQL:** PlanetScale / Railway / Render managed DB
- **MongoDB:** MongoDB Atlas

---

---

## English

### What is this?

**My Waze** is a smart web application for grocery shopping management.  
Users upload a receipt image (or capture one directly with the camera), the system automatically extracts products using AI (Google Gemini), and then lets them compare the shopping basket across different store branches by price.

---

### Main Features

| Feature | Description |
|---|---|
| **Receipt Scanning** | Upload an image or capture directly from camera |
| **AI-based OCR** | Automatic extraction of products and prices from Hebrew receipts |
| **Cart Management** | Add, edit and delete products in the cart |
| **Price Comparison** | Compare the basket against all stores in the database |
| **Price History** | Store product prices over time per branch |
| **Popular Products** | Display frequently used products on the dashboard |
| **User Authentication** | Registration, login, secure JWT sessions |

---

### Architecture

The application is split into three independent services:

```
┌─────────────────────────────────────────────────────┐
│               Browser (React)                        │
│          Vite + React 19 + Tailwind                  │
└────────────┬─────────────────────┬───────────────────┘
             │                     │
             ▼                     ▼
┌────────────────────┐   ┌─────────────────────────────┐
│  server_auth       │   │  backend_server              │
│  Node.js + Express │   │  Python + FastAPI            │
│  MongoDB           │   │  MySQL + Gemini AI           │
│  PORT: 5000        │   │  PORT: 8000                  │
└────────────────────┘   └─────────────────────────────┘
```

| Layer | Technology | Responsibility |
|---|---|---|
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, React Router 7 | User interface |
| **Auth Server** | Node.js, Express 4, MongoDB, JWT, bcryptjs | Users, login, cart, popular products |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, MySQL 8, Gemini AI | Receipt OCR, price comparison, product catalog |

---

### Folder Structure

```
my_waze/
├── client/                        # Frontend (React + Vite)
│   ├── src/
│   │   ├── Pages/                 # Pages: Auth, Dashboard, Cart, Scan, Details, Compare
│   │   ├── Comps/                 # Components: Auth, Cart, Dashboard, Scan
│   │   ├── hooks/                 # Custom hooks: useAuth, useCart, useCompare, useCameraCapture
│   │   ├── Contexts/              # AuthContext
│   │   └── test/                  # setupTests.js
│   ├── .env.example
│   └── vite.config.js
│
├── server_auth/                   # Auth server (Node.js + Express)
│   ├── controllers/               # authController, cartController, productsController
│   ├── models/                    # User (MongoDB)
│   ├── routes/                    # auth, cart, products
│   ├── middleware/                # auth.js (JWT protect)
│   ├── db/                        # MongoDB client
│   └── .env.example
│
└── backend_server/                # Data server (Python + FastAPI)
    ├── app/
    │   ├── api/                   # receipt_routes, basket_routes, products_routes
    │   ├── services/              # OCRService, ReceiptService, BasketService
    │   ├── models/                # Product, Store, PriceHistory (SQLAlchemy)
    │   ├── schemas/               # Pydantic schemas
    │   └── core/                  # config, constants, enums
    ├── migrations/                # Alembic migrations
    ├── dockerfile
    ├── docker-compose.yml
    └── .env.example
```

---

### Local Setup

#### Prerequisites

- Node.js 18+
- Python 3.11+
- MongoDB running locally (or Atlas)
- MySQL 8 running locally (or Docker)
- Google Gemini API key

---

#### 1. Frontend (client)

```bash
cd client
cp .env.example .env
# Edit .env as needed
npm install
npm run dev
```

Runs at: `http://localhost:5173`

**Environment variables:**
```env
VITE_API_URL=http://localhost:5000/api        # Auth server
VITE_DATA_API_URL=http://localhost:8000       # Backend server
```

---

#### 2. Auth Server (server_auth)

```bash
cd server_auth
cp .env.example .env
# Edit .env as needed
npm install
node index.js
```

Runs at: `http://localhost:5000`

**Environment variables:**
```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=my_waze
JWT_SECRET=your_jwt_secret
JWT_EXPIRES_IN=7d
PORT=5000
CLIENT_URL=http://localhost:5173
```

---

#### 3. Backend Server (backend_server)

**With Docker (recommended):**
```bash
cd backend_server
docker-compose up -d       # Starts MySQL only
cp .env.example .env
# Edit .env with GEMINI_API_KEY and SQLALCHEMY_DATABASE_URL
pip install -r requirements.txt
alembic upgrade head       # Run migrations
uvicorn app.main:app --reload --port 8000
```

**Environment variables:**
```env
SQLALCHEMY_DATABASE_URL=mysql+pymysql://user:password@localhost:3306/grocery_app
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-1.5-flash
CORS_ALLOW_ORIGINS=http://localhost:5173
CREATE_TABLES_ON_STARTUP=false
```

Runs at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

---

### API Endpoints

#### Backend (FastAPI) — `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| `POST` | `/receipts/upload` | Upload receipt image for OCR extraction |
| `POST` | `/basket/compare` | Compare shopping basket across stores |
| `GET` | `/products` | List products with search |

#### Auth Server (Express) — `http://localhost:5000/api`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/auth/register` | ❌ | Register user |
| `POST` | `/auth/login` | ❌ | Login |
| `GET` | `/auth/me` | ✅ JWT | Current user info |
| `GET` | `/products` | ✅ JWT | Product list |
| `GET` | `/products/popular` | ✅ JWT | Popular products |
| `GET/POST/PATCH/DELETE` | `/cart` | ✅ JWT | Cart management |
| `PUT` | `/cart/store` | ✅ JWT | Update selected store |

---

### Testing

```bash
cd client
npm run test        # Run all tests with Vitest
npm run lint        # ESLint check
npm run build       # Verify production build
```

---

### Deployment

- **Frontend:** Render / Vercel / Netlify — run `npm run build` then deploy `dist/`
- **Backend (FastAPI):** Render / Railway — built-in `dockerfile` included
- **Auth Server:** Render / Railway — `node index.js`
- **MySQL:** PlanetScale / Railway / Render managed DB
- **MongoDB:** MongoDB Atlas
