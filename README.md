# Adventure Land

A desktop web application for a fictional fantasy guild. Adventurers discover quests, reserve session places, and manage their participation. Guild Masters create quests and schedule sessions across different locations.

Built by **Abolfazl Mahmoodi** as a final project for *Introduction to Web Applications* at Politecnico di Torino.

## Demo status

The previous PythonAnywhere deployment is currently offline. The application can be run locally.

The interface is designed for **desktop browsers**. Mobile support is outside the current project scope.

## Features

### Adventurers

- Sign up, log in, edit a profile, and upload an avatar.
- Filter quest sessions by day, quest type, difficulty, and character role.
- Reserve one place or bring a companion with a separate role.
- View, edit, and cancel participation subject to scheduling rules.
- Post comments and delete their own comments.
- Explore heroes, locations, player profiles, and an adventurer leaderboard.

### Guild Masters

- Access a dedicated management dashboard.
- Create quests with descriptions, artwork, difficulty, and duration.
- Schedule sessions by day, time, and location.
- Edit or cancel sessions that have no participants.

## Scheduling and reservation rules

- An adventurer can join at most three sessions in the fictional week.
- A reservation covers one or two places, subject to role availability.
- A player cannot join overlapping sessions or sessions that have already started.
- Participation changes and cancellations require more than eight hours before the session starts.
- Sessions at the same location cannot overlap and must finish by midnight.

Time is based on a simulated day and clock stored in the database, rather than a live calendar.

## Technologies

Python, Flask, Flask-Login, Werkzeug password hashing, SQLite, Jinja templates, HTML, CSS, Bootstrap 5.3.8, and Google Fonts.

## Run locally

Use a Python version compatible with `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in a desktop browser. Bootstrap and Google Fonts need an internet connection.

### Demo accounts

The included database contains anonymized demo identities, eight quests, sixteen sessions, and sample reservations. Original email addresses, password hashes, personal profile details, comments, and avatar files have been removed or replaced.

To use an existing account, configure a password locally before starting the app:

```bash
python set_demo_password.py
```

Choose `demo_guildmaster` for the management dashboard, or one of the listed `demo_adventurer_` accounts for reservations. Password input is hidden and only a password hash is stored. You can also register a new adventurer through the signup page.

Use a disposable local database. Do not commit it after entering personal information or configuring passwords you use elsewhere.

## Structure

```text
AdventureLand/
├── app.py                 # Routes, authentication, and forms
├── dao.py                 # SQLite queries and persistence
├── quest_logic.py         # Participation validation
├── week_time.py           # Simulated week calculations
├── set_demo_password.py   # Local demo-account setup
├── requirements.txt
├── database/guild.db      # Anonymized demo database
├── templates/             # 19 Jinja templates
└── static/
    ├── css/style.css
    └── images/
```

## Deployment

This application needs a Python-capable host and writable storage for SQLite and uploaded images. GitHub Pages cannot run its Flask backend.

For hosting, configure a stable session secret through the `SECRET_KEY` environment variable and keep debug mode disabled. Before public deployment, review form CSRF protection, file-upload validation and size limits, and concurrent reservation handling.

## Portfolio focus

Adventure Land demonstrates server-rendered web development, authentication, access control for two user roles, relational data modelling, form validation, and reservation logic involving time conflicts and limited capacity.

## Assets

Fantasy artwork is included for the academic demonstration. Document asset origins and usage permissions before distributing artwork under a project-wide license.
