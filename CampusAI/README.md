# CampusAI

Campus complaint system. Students report issues in 3 categories, the complaint goes straight to the right staff member, AI analyzes it, and the status is tracked (pending → in-progress → resolved).

| Category       | Goes to          | Staff PIN (change in `config.py`) |
|----------------|------------------|-----------------------------------|
| Discipline     | Discipline Head  | 1111 |
| Cleanliness    | Peon In-charge   | 2222 |
| Infrastructure | Director         | 3333 |

## Run in VS Code

1. Install Python 3.9+ (check with `python --version`).
2. In VS Code: **File → Open Folder → CampusAI**.
3. Open the terminal (Ctrl + `) and run:

   ```
   python server.py
   ```
   (On Mac/Linux use `python3 server.py`.) Or press **F5** (a launch config is included).
4. Open in browser:
   - Student page: http://127.0.0.1:8000
   - Staff dashboard: http://127.0.0.1:8000/staff

No `pip install` needed - only Python's standard library is used.

## Folder structure

```
CampusAI/
├── server.py          # HTTP server + API routes
├── config.py          # categories, routing, staff PINs, settings
├── database.py        # SQLite database (data/campusai.db, auto-created)
├── ai_analyzer.py     # AI priority / summary / category check
├── static/
│   ├── index.html     # student page (submit + track)
│   ├── app.js
│   ├── staff.html     # staff dashboard
│   ├── staff.js
│   └── style.css
├── uploads/           # complaint photos
├── data/              # database file
└── .vscode/launch.json
```

## AI analysis

By default a built-in rule-based analyzer sets priority (High/Medium/Low), a short summary, tags, and warns staff if the text looks like a different category.

To use Claude instead, set an API key before starting the server:

```
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-key"; python server.py
# Mac/Linux
ANTHROPIC_API_KEY=your-key python3 server.py
```
If the API call fails, it falls back to the built-in analyzer automatically.

## API (for reference)

- `POST /api/complaints` - submit (category, description, location, photo as base64, student_name, student_id)
- `GET /api/track/<ticket>` - status + history
- `GET /api/my-complaints?student_id=...`
- `POST /api/staff/login` - role + PIN → token
- `GET /api/staff/complaints?status=...`, `GET /api/staff/stats`
- `PATCH /api/staff/complaints/<id>` - change status (only your own category)

## Before real use

- Change the PINs in `config.py`.
- Put it behind HTTPS and a proper login system if deployed publicly.
