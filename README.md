# CS 5330 Group Project — Setup & Run Guide

## Requirements

- Python 3.10+
- MySQL 8.0+ or MariaDB 10.6+

---

## 1. Create the database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE social_media_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

Then load the schema:

```bash
mysql -u root -p social_media_db < schema.sql
```

---

## 2. Configure credentials

Edit `db_config.json`:

```json
{
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "your_password_here",
  "database": "social_media_db"
}
```

---

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Run the backend

```bash
python app.py
```

Flask will start at **http://localhost:5000**.

---

## 5. Open the frontend

Open `index.html` directly in your browser (double-click), or serve it:

```bash
python -m http.server 8080
# then visit http://localhost:8080
```

---

## API Reference

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/projects` | Create project + fields |
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/<name>/fields` | List fields for a project |
| POST | `/api/projects/<name>/fields` | Add a field to a project |
| POST | `/api/posts` | Submit a post |
| GET | `/api/posts` | Query posts (filters: platform, username, first_name, last_name, from, to) |
| POST | `/api/analysis` | Save analysis results (partial allowed) |
| GET | `/api/experiments/<name>` | Get all posts + results + coverage for a project |
| POST | `/api/persons/link` | Link accounts to a person |
| POST | `/api/accounts` | Create/ensure a user account |
| POST | `/api/platforms` | Create/ensure a platform |
| GET | `/api/platforms` | List platforms |
| POST | `/api/institutions` | Create/ensure an institution |
| GET | `/api/institutions` | List institutions |

---

## Notes

- All routes return JSON.
- POST `/api/posts` auto-creates the Platform and UserAccount rows if they don't exist yet.
- POST `/api/persons/link` auto-creates a Person if `unique_id` is omitted.
- Analysis results may be partial — not every field needs a value.
- The `db_config.json` file **must be included** in your submission per project requirements.
