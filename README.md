
```
███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
              U S E R   A P I   v 1.0
```

> *"Not just endpoints. A whole API ecosystem with live dashboard, audit trail, and real validation — in one Python file."*

---

## 🧠 What This Actually Is

Most Flask API projects are 30 lines with a dict and no error handling.

This is different.

NEXUS is a **production-patterned REST API** — full CRUD, request middleware, input validation, audit logging, live stats, pagination, filtering, and a **browser dashboard** you can open and interact with without touching a terminal. It ships with 5 pre-seeded users so it's never empty on first run.

One Python file. Open it in VS Code. Read it top to bottom in 10 minutes. Understand every pattern used in real production APIs.

---

## 🗺️ Endpoint Map

```
  BASE: http://127.0.0.1:5000

  ┌──────────────────────────────────────────────────────────────┐
  │  METHOD   ROUTE                   DESCRIPTION                │
  ├──────────────────────────────────────────────────────────────┤
  │  GET      /                       API info + endpoint list   │
  │  GET      /health                 Health check               │
  ├──────────────────────────────────────────────────────────────┤
  │  GET      /api/users              List + filter + paginate   │
  │  GET      /api/users/<id>         Get single user            │
  │  POST     /api/users              Create user                │
  │  PUT      /api/users/<id>         Full replace               │
  │  PATCH    /api/users/<id>         Partial update             │
  │  DELETE   /api/users/<id>         Delete user                │
  ├──────────────────────────────────────────────────────────────┤
  │  GET      /api/stats              Live API statistics        │
  │  GET      /api/audit              Audit trail (last 50)      │
  └──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run
python app.py

# 3. Open the live dashboard
open demo.html        # macOS
start demo.html       # Windows
xdg-open demo.html    # Linux

# OR use cURL directly
curl http://127.0.0.1:5000/api/users
```

---

## 📁 Project Structure

```
nexus-api/
│
├── 🐍  app.py              ← The entire API. One clean file.
├── 🌐  demo.html           ← Live browser dashboard (no server needed)
├── 📦  requirements.txt    ← flask + flask-cors
└── 📖  README.md           ← You're reading it
```

---

## 📡 API Reference

### GET /api/users

Supports filtering, sorting, searching, and pagination.

```bash
# All users
curl http://127.0.0.1:5000/api/users

# Filter by role
curl "http://127.0.0.1:5000/api/users?role=admin"

# Filter by department
curl "http://127.0.0.1:5000/api/users?dept=Engineering"

# Search by name or email
curl "http://127.0.0.1:5000/api/users?search=arjun"

# Paginate
curl "http://127.0.0.1:5000/api/users?page=1&limit=5"

# Sort
curl "http://127.0.0.1:5000/api/users?sort=name&dir=asc"

# Combine everything
curl "http://127.0.0.1:5000/api/users?role=developer&dept=Engineering&sort=name&page=1&limit=3"
```

**Response:**
```json
{
  "success": true,
  "message": "Found 5 user(s)",
  "data": [ {...}, {...} ],
  "meta": {
    "total": 5,
    "page": 1,
    "limit": 20,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### POST /api/users

```bash
curl -X POST http://127.0.0.1:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Zara Khan",
    "email": "zara@nexus.io",
    "role": "designer",
    "department": "Product",
    "age": 26
  }'
```

**Required fields:** `name`, `email`  
**Optional:** `role`, `department`, `age`, `active`

---

### PUT /api/users/:id  *(full replace)*

```bash
curl -X PUT http://127.0.0.1:5000/api/users/<id> \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Zara Khan",
    "email": "zara.new@nexus.io",
    "role": "manager",
    "department": "Operations"
  }'
```

---

### PATCH /api/users/:id  *(partial update)*

```bash
# Only update what you pass — everything else stays the same
curl -X PATCH http://127.0.0.1:5000/api/users/<id> \
  -H "Content-Type: application/json" \
  -d '{"role": "admin", "active": false}'
```

---

### DELETE /api/users/:id

```bash
curl -X DELETE http://127.0.0.1:5000/api/users/<id>
```

---

### GET /api/stats

```bash
curl http://127.0.0.1:5000/api/stats
```

Returns live counts for requests, users by role, users by department, audit events, and more.

---

### GET /api/audit

```bash
curl http://127.0.0.1:5000/api/audit?limit=10
```

Returns the last N API operations — who did what, when, and what changed.

---

## ✅ Validation Rules

| Field | Rules |
|---|---|
| `name` | Required, string, min 2 chars |
| `email` | Required, valid format, globally unique |
| `role` | Must be: `admin`, `developer`, `designer`, `manager`, `analyst`, `intern` |
| `department` | Must be: `Engineering`, `Product`, `Operations`, `Marketing`, `Finance`, `HR` |
| `age` | Integer, 16–100 |

**Validation error response (422):**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    "'email' must be a valid email address",
    "'role' must be one of: admin, analyst, ..."
  ]
}
```

---

## 🔍 What's Under The Hood

```python
# Every request is counted by middleware
@app.before_request
def count_request():
    API_STATS["total_requests"] += 1
    API_STATS["requests_by_method"][request.method] += 1

# Every operation is audited
def audit(action, resource, resource_id=None, detail=""):
    AUDIT_LOG.append({
        "timestamp": now_iso(),
        "action": action,
        "resource_id": resource_id,
        "detail": detail,
    })

# Consistent response shape everywhere
def success(data, message="OK", status=200, meta=None):
    ...

def error(message, status=400, errors=None):
    ...
```

---

## 🌐 Live Dashboard Features

Open `demo.html` in any browser while Flask is running.

Live demo link: [Open the dashboard locally](demo.html)

| Feature | Description |
|---|---|
| **Live status ping** | Auto-detects if Flask is running |
| **Stats strip** | Real-time user count, request count, audit events |
| **User table** | All users with search, role filter, department filter |
| **Quick edit** | Click "edit" on any row to pre-fill the PUT form |
| **POST / PUT / PATCH / DELETE tabs** | Test every endpoint from the browser |
| **JSON response viewer** | Colour-highlighted response for every operation |
| **Audit trail** | Live feed of all API operations |
| **cURL cheatsheet** | Copy-paste ready commands for every endpoint |

---

## 🛠️ Tech Stack

| Tool | Role |
|---|---|
| `Flask` | Web framework — routes, request handling |
| `flask-cors` | Allows browser dashboard to call the API |
| `uuid` | Generates unique user IDs |
| `re` | Email validation regex |
| `datetime` | ISO timestamps on every record |
| Pure Python `dict` | In-memory data store (no database needed) |

---

## 🔌 Testing with Postman

1. Import a new request
2. Set method and URL (e.g. `POST http://127.0.0.1:5000/api/users`)
3. Under Body → raw → JSON, paste the payload
4. Hit Send

All responses follow the same shape: `{ success, message, data, meta? }`

---

## 📜 License

MIT. Clone it, extend it, use it as a base.

---

```
  One file. Nine endpoints. Middleware, validation,
  audit logs, pagination, live dashboard.

  This is what "done properly" looks like.

  — NEXUS API  🔮
```
