# Student Academic Performance Analysis System

A Flask web application that analyzes student marks and attendance.

## Features
- Teacher login (session based)
- Dashboard: class average, pass rate, at-risk count, attendance–marks correlation
- Charts: subject averages, grade distribution, attendance vs percentage
- Automatic total, percentage, grade, rank, pass/fail
- At-risk detection (percentage < 50, attendance < 75, or any subject < 40)
- K-Means clustering into performance groups (scikit-learn)
- Linear Regression prediction of percentage from attendance (scikit-learn)
- Add / delete students, search, per-student report with class comparison
- CSV import and CSV report export; student names are unique, existing duplicates are cleaned up on startup, and repeated names are skipped on import
- SQLite database (created automatically with 20 sample students)

## Setup
```
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 and log in with **admin / admin123**.

## Change the login
Set environment variables before running: `ADMIN_USER`, `ADMIN_PASS`, `SECRET_KEY`.

## Project structure
```
app.py          routes and login
database.py     SQLite + CSV import
analysis.py     calculations, clustering, prediction
templates/      HTML pages (Jinja2)
static/         CSS
data/           sample_students.csv
```

## CSV format
`Name,Maths,Physics,Chemistry,English,CS,Attendance`

## Future scope
Student login, PDF reports, email alerts to at-risk students, more subjects/semesters.
