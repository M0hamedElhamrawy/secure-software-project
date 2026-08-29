# Campus Notes Portal

## Project Overview

Campus Notes Portal is a small web application for a university course
community. Students can browse a course catalog, look up classmates in a
directory, download course materials, and post personal study notes tied to a
course. Administrators have a separate dashboard for managing registered
users and moderating notes.

The application is built with Python, Flask, and SQLite, and renders plain
HTML/CSS templates on the server.

## Requirements

```text
Python 3.10+
pip
```

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The database is created and seeded automatically the first time the
application starts — no manual setup steps are required.

## URL

```text
http://127.0.0.1:5000
```

## Demo Accounts

| Role  | Email                     | Password    |
|-------|---------------------------|-------------|
| Admin | admin@example.local       | Admin123!   |
| User  | student@example.local     | Student123! |

## Basic Troubleshooting

- If the application fails to start, confirm dependencies installed
  successfully with `pip install -r requirements.txt`.
- The SQLite database file is created automatically at
  `data/application.db`. If you want to reset all data, stop the
  application and delete the `data/application.db` file, then restart it.
- The app listens on port 5000 by default. If that port is already in use,
  stop the other process or edit the port number in `app.py`.
