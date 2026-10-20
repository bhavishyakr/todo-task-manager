# TaskFlow – To-Do Task Manager

A full-stack task manager built after completing Python training.

| Layer     | Technology                                  |
|-----------|---------------------------------------------|
| Backend   | Python 3, Flask (REST API), sessions        |
| Database  | SQLite (built into Python, no setup needed) |
| Frontend  | HTML5, CSS3, vanilla JavaScript (fetch API) |
| Security  | Password hashing (Werkzeug), per-user data isolation |

## Features
- Register, log in and log out (passwords are hashed, never stored as plain text)
- Add, edit, delete and complete tasks
- Title, details, category, priority (low/medium/high) and due date
- Search, filter by status / category / priority, and sort
- Overdue detection, "due today" summary and a progress ring
- Clear all completed tasks in one click
- Input validation on the server, responsive layout, keyboard accessible
- Automated tests for the API

## Project structure
```
todo-task-manager/
├── app.py               # Flask app: database, auth, REST API, pages
├── requirements.txt
├── templates/
│   ├── auth.html        # login / register page
│   └── index.html       # main task manager page
├── static/
│   ├── css/style.css
│   └── js/
│       ├── auth.js      # login / register logic
│       └── app.js       # task manager logic
└── tests/test_app.py    # unit tests
```

## Run it
```bash
# 1. (optional) create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 2. install dependency
pip install -r requirements.txt

# 3. start the server
python app.py
```
Open **http://127.0.0.1:5000** in your browser, create an account and start adding tasks.
The database file `taskflow.db` is created automatically on first run.

## Run the tests
```bash
python tests/test_app.py
```

## REST API
| Method | Endpoint                     | Purpose                         |
|--------|------------------------------|---------------------------------|
| POST   | /api/register                | Create account                  |
| POST   | /api/login                   | Log in                          |
| POST   | /api/logout                  | Log out                         |
| GET    | /api/me                      | Current user                    |
| GET    | /api/tasks                   | List tasks (`status`, `priority`, `category`, `search`, `sort`) |
| POST   | /api/tasks                   | Create task                     |
| PUT    | /api/tasks/<id>              | Update task                     |
| PATCH  | /api/tasks/<id>/toggle       | Mark done / not done            |
| DELETE | /api/tasks/<id>              | Delete task                     |
| DELETE | /api/tasks/completed         | Delete all completed tasks      |
| GET    | /api/stats                   | Counts, progress and categories |

## Ideas to extend it
- Task reminders by email
- Drag-and-drop ordering
- Dark mode toggle
- Deploy on Render / PythonAnywhere (set the `SECRET_KEY` environment variable)
