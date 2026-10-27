"""Student Academic Performance Analysis System - Flask app."""
import io
import os
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, session, url_for)

import analysis as an
import database as db

# Initialize the SQLite database as soon as the app is imported so the
# application works reliably when run with a WSGI server or test client.
db.init_db()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["user"] = ADMIN_USER
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    df = an.compute(db.get_df())
    if df.empty:
        return render_template("dashboard.html", empty=True)
    return render_template(
        "dashboard.html", empty=False, s=an.summary(df), subj=an.subject_stats(df),
        grades=an.grade_distribution(df), grade_labels=an.GRADES,
        top=df.sort_values("Rank").head(5).to_dict("records"),
        risk=df[df["AtRisk"]].sort_values("Percentage").to_dict("records"),
        scatter=df[["Attendance", "Percentage"]].to_dict("records"))


@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip().lower()
    df = an.compute(db.get_df())
    rows = []
    if not df.empty:
        if q:
            df = df[df["Name"].str.lower().str.contains(q, regex=False)]
        rows = df.sort_values("Rank").to_dict("records")
    return render_template("students.html", rows=rows, q=q, subjects=db.SUBJECTS)


@app.post("/students/add")
@login_required
def add_student():
    name = request.form.get("name", "").strip()
    try:
        vals = [float(request.form[k]) for k in ["maths", "physics", "chemistry", "english", "cs", "attendance"]]
    except (KeyError, ValueError):
        flash("Enter valid numbers for all fields.", "error")
        return redirect(url_for("students"))
    if not name or any(v < 0 or v > 100 for v in vals):
        flash("Name is required and values must be between 0 and 100.", "error")
    else:
        try:
            db.add_student(name, vals)
        except ValueError as e:
            flash(str(e), "error")
        else:
            flash(f"Added {name}.", "ok")
    return redirect(url_for("students"))


@app.post("/students/<int:sid>/delete")
@login_required
def delete_student(sid):
    db.delete_student(sid)
    flash("Student deleted.", "ok")
    return redirect(url_for("students"))


@app.route("/students/<int:sid>")
@login_required
def student_detail(sid):
    df = an.compute(db.get_df())
    row = df[df["ID"] == sid]
    if row.empty:
        abort(404)
    return render_template("student.html", st=row.iloc[0].to_dict(), subjects=db.SUBJECTS,
                           marks=[float(row.iloc[0][s]) for s in db.SUBJECTS],
                           class_avg=[round(float(df[s].mean()), 1) for s in db.SUBJECTS],
                           total_students=len(df))


@app.post("/upload")
@login_required
def upload():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".csv"):
        flash("Please choose a .csv file.", "error")
        return redirect(url_for("students"))
    try:
        added, skipped = db.load_csv(file, replace=request.form.get("replace") == "1")
        message = f"Imported {added} students."
        if skipped:
            message += f" Skipped {skipped} duplicate name{'s' if skipped != 1 else ''}."
        flash(message, "ok")
    except Exception as e:  # shown to the teacher as a friendly message
        flash(f"Upload failed: {e}", "error")
    return redirect(url_for("students"))


@app.route("/export")
@login_required
def export():
    df = an.compute(db.get_df())
    cols = ["Rank", "Name", *db.SUBJECTS, "Total", "Percentage", "Grade", "Attendance", "Result", "Group"]
    buf = io.BytesIO(df.sort_values("Rank")[cols].to_csv(index=False).encode())
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="performance_report.csv")


@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    df = an.compute(db.get_df())
    fitted = an.fit_model(df) if not df.empty else None
    result = att = None
    if fitted is None and request.method == "POST":
        flash("Add at least 5 students to train the prediction model.", "error")
    elif request.method == "POST":
        try:
            att = min(max(float(request.form["attendance"]), 0), 100)
            result = round(float(min(max(fitted[0].predict([[att]])[0], 0), 100)), 1)
        except (KeyError, ValueError):
            flash("Enter a valid attendance percentage.", "error")
    return render_template("predict.html", fitted=fitted, result=result, att=att,
                           points=df[["Attendance", "Percentage"]].to_dict("records") if fitted else [])


if __name__ == "__main__":
    app.run(debug=True)
