#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║                    N E X U S   U S E R   A P I                   ║
║              Flask REST API  ·  v1.0  ·  Full CRUD               ║
╚═══════════════════════════════════════════════════════════════════╝

Endpoints:
  GET    /api/users          → list all users (filterable + paginated)
  GET    /api/users/<id>     → get single user
  POST   /api/users          → create user
  PUT    /api/users/<id>     → full update
  PATCH  /api/users/<id>     → partial update
  DELETE /api/users/<id>     → delete user
  GET    /api/stats          → live API statistics
  GET    /api/audit          → audit trail of all operations
  GET    /health             → health check
  GET    /                   → API info
"""

from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from datetime import datetime
from functools import wraps
import uuid, time, re

# ─────────────────────────────────────────────────────────────
#   A P P   I N I T
# ─────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)  # allow browser dashboard to call the API

app.config["JSON_SORT_KEYS"] = False

# ─────────────────────────────────────────────────────────────
#   I N - M E M O R Y   S T O R E
# ─────────────────────────────────────────────────────────────

USERS: dict = {}          # { user_id: user_dict }
AUDIT_LOG: list = []      # list of audit events
API_STATS: dict = {
    "total_requests"  : 0,
    "requests_by_method": {"GET": 0, "POST": 0, "PUT": 0, "PATCH": 0, "DELETE": 0},
    "total_users_created" : 0,
    "total_users_deleted" : 0,
    "started_at" : datetime.utcnow().isoformat() + "Z",
}

# Pre-seed with sample users so the API isn't empty on first run
SEED_USERS = [
    {"name": "Arjun Sharma",    "email": "arjun@nexus.io",   "role": "admin",     "department": "Engineering",  "age": 28},
    {"name": "Priya Nair",      "email": "priya@nexus.io",   "role": "developer", "department": "Engineering",  "age": 25},
    {"name": "Rohit Verma",     "email": "rohit@nexus.io",   "role": "designer",  "department": "Product",      "age": 30},
    {"name": "Sneha Iyer",      "email": "sneha@nexus.io",   "role": "manager",   "department": "Operations",   "age": 34},
    {"name": "Karthik Menon",   "email": "karthik@nexus.io", "role": "developer", "department": "Engineering",  "age": 27},
]

for _u in SEED_USERS:
    _id = str(uuid.uuid4())
    USERS[_id] = {
        "id"         : _id,
        "name"       : _u["name"],
        "email"      : _u["email"],
        "role"       : _u["role"],
        "department" : _u["department"],
        "age"        : _u["age"],
        "active"     : True,
        "created_at" : datetime.utcnow().isoformat() + "Z",
        "updated_at" : datetime.utcnow().isoformat() + "Z",
    }
    API_STATS["total_users_created"] += 1

# ─────────────────────────────────────────────────────────────
#   H E L P E R S   &   M I D D L E W A R E
# ─────────────────────────────────────────────────────────────

VALID_ROLES  = {"admin", "developer", "designer", "manager", "analyst", "intern"}
VALID_DEPTS  = {"Engineering", "Product", "Operations", "Marketing", "Finance", "HR"}
EMAIL_REGEX  = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def audit(action: str, resource: str, resource_id: str = None, detail: str = ""):
    """Append an event to the audit trail."""
    AUDIT_LOG.append({
        "id"          : str(uuid.uuid4())[:8],
        "timestamp"   : now_iso(),
        "action"      : action,
        "resource"    : resource,
        "resource_id" : resource_id,
        "ip"          : request.remote_addr,
        "detail"      : detail,
    })
    if len(AUDIT_LOG) > 200:           # keep last 200 events
        AUDIT_LOG.pop(0)

def success(data=None, message="OK", status=200, meta=None):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    if meta:
        body["meta"] = meta
    return jsonify(body), status

def error(message: str, status=400, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status

def validate_user_payload(data: dict, partial=False) -> list:
    """Return a list of validation error strings."""
    errs = []
    if not partial:
        for field in ("name", "email"):
            if field not in data:
                errs.append(f"'{field}' is required")

    if "name" in data:
        if not isinstance(data["name"], str) or len(data["name"].strip()) < 2:
            errs.append("'name' must be a string with at least 2 characters")

    if "email" in data:
        if not EMAIL_REGEX.match(str(data["email"])):
            errs.append("'email' must be a valid email address")
        # uniqueness check (skip current user on update via caller)
        if any(u["email"] == data["email"] for u in USERS.values()):
            errs.append(f"'email' {data['email']} is already registered")

    if "role" in data and data["role"] not in VALID_ROLES:
        errs.append(f"'role' must be one of: {', '.join(sorted(VALID_ROLES))}")

    if "department" in data and data["department"] not in VALID_DEPTS:
        errs.append(f"'department' must be one of: {', '.join(sorted(VALID_DEPTS))}")

    if "age" in data:
        if not isinstance(data["age"], int) or not (16 <= data["age"] <= 100):
            errs.append("'age' must be an integer between 16 and 100")

    return errs

@app.before_request
def count_request():
    """Middleware: count every incoming request."""
    API_STATS["total_requests"] += 1
    method = request.method
    if method in API_STATS["requests_by_method"]:
        API_STATS["requests_by_method"][method] += 1

# ─────────────────────────────────────────────────────────────
#   R O U T E S
# ─────────────────────────────────────────────────────────────

# ── Root ──────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def root():
    return success({
        "name"       : "NEXUS User API",
        "version"    : "1.0.0",
        "description": "A production-grade in-memory REST API for user management",
        "endpoints"  : {
            "GET    /api/users"         : "List all users (supports ?role=, ?dept=, ?active=, ?page=, ?limit=, ?search=)",
            "GET    /api/users/<id>"    : "Get a single user by ID",
            "POST   /api/users"         : "Create a new user",
            "PUT    /api/users/<id>"    : "Full update (replaces all fields)",
            "PATCH  /api/users/<id>"    : "Partial update (only provided fields)",
            "DELETE /api/users/<id>"    : "Delete a user",
            "GET    /api/stats"         : "Live API statistics",
            "GET    /api/audit"         : "Audit trail of all operations",
            "GET    /health"            : "Health check",
        },
        "docs": "Open demo.html in your browser for a live interactive dashboard",
    })

# ── Health check ──────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return success({
        "status"     : "healthy",
        "uptime_since": API_STATS["started_at"],
        "user_count" : len(USERS),
        "timestamp"  : now_iso(),
    }, message="API is healthy")

# ── GET /api/users — list with filter + pagination ────────────
@app.route("/api/users", methods=["GET"])
def get_users():
    users = list(USERS.values())

    # — filters —
    role   = request.args.get("role")
    dept   = request.args.get("dept")
    active = request.args.get("active")
    search = request.args.get("search", "").lower().strip()

    if role:
        users = [u for u in users if u["role"] == role]
    if dept:
        users = [u for u in users if u["department"] == dept]
    if active is not None:
        flag = active.lower() not in ("false", "0", "no")
        users = [u for u in users if u["active"] == flag]
    if search:
        users = [u for u in users if
                 search in u["name"].lower() or
                 search in u["email"].lower() or
                 search in u.get("department", "").lower()]

    # — sort —
    sort_by  = request.args.get("sort", "created_at")
    sort_dir = request.args.get("dir", "desc")
    if sort_by in ("name", "email", "role", "department", "age", "created_at"):
        users.sort(key=lambda u: u.get(sort_by, ""), reverse=(sort_dir == "desc"))

    # — pagination —
    total = len(users)
    try:
        page  = max(1, int(request.args.get("page", 1)))
        limit = max(1, min(100, int(request.args.get("limit", 20))))
    except ValueError:
        page, limit = 1, 20

    start  = (page - 1) * limit
    paged  = users[start: start + limit]
    pages  = max(1, -(-total // limit))   # ceil div

    audit("LIST", "users", detail=f"returned {len(paged)}/{total}")

    return success(
        paged,
        message=f"Found {total} user(s)",
        meta={
            "total"     : total,
            "page"      : page,
            "limit"     : limit,
            "pages"     : pages,
            "has_next"  : page < pages,
            "has_prev"  : page > 1,
            "filters"   : {"role": role, "dept": dept, "active": active, "search": search or None},
        }
    )

# ── GET /api/users/<id> — single user ─────────────────────────
@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    user = USERS.get(user_id)
    if not user:
        audit("GET", "users", user_id, "not found")
        return error(f"User '{user_id}' not found", 404)

    audit("GET", "users", user_id)
    return success(user, message="User retrieved")

# ── POST /api/users — create ───────────────────────────────────
@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return error("Request body must be valid JSON", 400)

    errs = validate_user_payload(data)
    if errs:
        return error("Validation failed", 422, errors=errs)

    uid = str(uuid.uuid4())
    user = {
        "id"         : uid,
        "name"       : data["name"].strip(),
        "email"      : data["email"].strip().lower(),
        "role"       : data.get("role", "developer"),
        "department" : data.get("department", "Engineering"),
        "age"        : data.get("age", None),
        "active"     : data.get("active", True),
        "created_at" : now_iso(),
        "updated_at" : now_iso(),
    }
    USERS[uid] = user
    API_STATS["total_users_created"] += 1
    audit("CREATE", "users", uid, f"created user '{user['name']}'")

    return success(user, message="User created successfully", status=201)

# ── PUT /api/users/<id> — full update ─────────────────────────
@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return error(f"User '{user_id}' not found", 404)

    data = request.get_json(silent=True)
    if not data:
        return error("Request body must be valid JSON", 400)

    # For PUT, allow same email if it belongs to this user
    temp_users = {k: v for k, v in USERS.items() if k != user_id}
    orig_users = USERS.copy()
    # temporarily replace store for uniqueness check
    USERS.clear()
    USERS.update(temp_users)
    errs = validate_user_payload(data, partial=False)
    USERS.clear()
    USERS.update(orig_users)

    if errs:
        return error("Validation failed", 422, errors=errs)

    updated = {
        "id"         : user_id,
        "name"       : data["name"].strip(),
        "email"      : data["email"].strip().lower(),
        "role"       : data.get("role", "developer"),
        "department" : data.get("department", "Engineering"),
        "age"        : data.get("age", user.get("age")),
        "active"     : data.get("active", True),
        "created_at" : user["created_at"],
        "updated_at" : now_iso(),
    }
    USERS[user_id] = updated
    audit("UPDATE", "users", user_id, "full update (PUT)")

    return success(updated, message="User updated successfully")

# ── PATCH /api/users/<id> — partial update ────────────────────
@app.route("/api/users/<user_id>", methods=["PATCH"])
def patch_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return error(f"User '{user_id}' not found", 404)

    data = request.get_json(silent=True)
    if not data:
        return error("Request body must be valid JSON", 400)

    # email uniqueness: skip self
    temp_check = {k: v for k, v in USERS.items() if k != user_id}
    orig_users = USERS.copy()
    USERS.clear()
    USERS.update(temp_check)
    errs = validate_user_payload(data, partial=True)
    USERS.clear()
    USERS.update(orig_users)

    if errs:
        return error("Validation failed", 422, errors=errs)

    allowed = {"name", "email", "role", "department", "age", "active"}
    for key in allowed:
        if key in data:
            user[key] = data[key].strip() if isinstance(data[key], str) else data[key]
    user["updated_at"] = now_iso()
    USERS[user_id] = user
    audit("PATCH", "users", user_id, f"patched fields: {list(data.keys())}")

    return success(user, message="User patched successfully")

# ── DELETE /api/users/<id> ────────────────────────────────────
@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return error(f"User '{user_id}' not found", 404)

    del USERS[user_id]
    API_STATS["total_users_deleted"] += 1
    audit("DELETE", "users", user_id, f"deleted user '{user['name']}'")

    return success(
        {"deleted_id": user_id, "deleted_user": user},
        message=f"User '{user['name']}' deleted successfully"
    )

# ── GET /api/stats ─────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def get_stats():
    roles = {}
    depts = {}
    for u in USERS.values():
        roles[u["role"]]           = roles.get(u["role"], 0) + 1
        depts[u["department"]]     = depts.get(u["department"], 0) + 1

    return success({
        **API_STATS,
        "current_user_count"   : len(USERS),
        "active_users"         : sum(1 for u in USERS.values() if u["active"]),
        "inactive_users"       : sum(1 for u in USERS.values() if not u["active"]),
        "users_by_role"        : roles,
        "users_by_department"  : depts,
        "audit_events"         : len(AUDIT_LOG),
    }, message="API statistics")

# ── GET /api/audit ─────────────────────────────────────────────
@app.route("/api/audit", methods=["GET"])
def get_audit():
    logs = list(reversed(AUDIT_LOG))   # newest first
    limit = min(50, int(request.args.get("limit", 20)))
    return success(
        logs[:limit],
        message=f"Showing last {min(limit, len(logs))} audit events",
        meta={"total_events": len(AUDIT_LOG), "showing": min(limit, len(logs))}
    )

# ─────────────────────────────────────────────────────────────
#   E R R O R   H A N D L E R S
# ─────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return error(f"Route not found: {request.path}", 404)

@app.errorhandler(405)
def method_not_allowed(e):
    return error(f"Method {request.method} not allowed on {request.path}", 405)

@app.errorhandler(500)
def server_error(e):
    return error("Internal server error", 500)

# ─────────────────────────────────────────────────────────────
#   R U N
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║              NEXUS USER API  ·  Starting up...              ║
╠══════════════════════════════════════════════════════════════╣
║  Base URL  :  http://127.0.0.1:5000                         ║
║  Health    :  http://127.0.0.1:5000/health                  ║
║  Users     :  http://127.0.0.1:5000/api/users               ║
║  Stats     :  http://127.0.0.1:5000/api/stats               ║
║  Audit     :  http://127.0.0.1:5000/api/audit               ║
║  Demo UI   :  open demo.html in your browser                ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host="0.0.0.0", port=5000)
