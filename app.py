import os
import secrets as _secrets
from flask import Flask, render_template, request, redirect, url_for, abort, session
from datetime import datetime, timedelta
from database import (
    get_connection, init_db,
    is_setup_complete, get_org_name, verify_password, run_setup, load_config,
)

app = Flask(__name__)

# ── Persistent secret key ─────────────────────────────────────────────────────
_KEY_FILE = os.path.join(os.path.dirname(__file__), ".secret_key")
if os.path.exists(_KEY_FILE):
    with open(_KEY_FILE) as _f:
        app.secret_key = _f.read().strip()
else:
    app.secret_key = _secrets.token_hex(32)
    with open(_KEY_FILE, "w") as _f:
        _f.write(app.secret_key)

FOLLOW_UP_THRESHOLD_DAYS = 30

init_db()

# ── Auth middleware ───────────────────────────────────────────────────────────

_PUBLIC = {"setup", "login", "logout", "static"}

@app.before_request
def guard():
    if not request.endpoint or request.endpoint in _PUBLIC:
        return
    if not is_setup_complete():
        return redirect(url_for("setup"))
    if not session.get("authenticated"):
        return redirect(url_for("login"))


# ── Setup (first run) ─────────────────────────────────────────────────────────

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if is_setup_complete():
        return redirect(url_for("contacts"))
    error = None
    if request.method == "POST":
        org_name = request.form["org_name"].strip()
        password = request.form["password"]
        confirm  = request.form["confirm"]
        if not org_name:
            error = "Organization name is required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            run_setup(org_name, password)
            session["authenticated"] = True
            return redirect(url_for("contacts"))
    return render_template("setup.html", error=error)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("contacts"))
    error = None
    if request.method == "POST":
        if verify_password(request.form["password"]):
            session["authenticated"] = True
            return redirect(url_for("contacts"))
        error = "Incorrect password. Please try again."
    return render_template("login.html", org_name=get_org_name(), error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Contacts ──────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return redirect(url_for("contacts"))


@app.route("/contacts")
def contacts():
    conn = get_connection()
    all_contacts = conn.execute("""
        SELECT c.*, MAX(i.interaction_date) as last_contact
        FROM contacts c
        LEFT JOIN interactions i ON i.contact_id = c.id
        GROUP BY c.id
        ORDER BY c.name
    """).fetchall()
    conn.close()
    return render_template("contacts.html", contacts=all_contacts, org_name=get_org_name())


@app.route("/contacts/add", methods=["POST"])
def add_contact():
    contact_type    = request.form["contact_type"]
    donation_amount = float(request.form["donation_amount"]) if contact_type == "donor" else 0.0
    conn = get_connection()
    conn.execute(
        "INSERT INTO contacts (name, email, phone, address, notes, donation_amount, contact_type) VALUES (?,?,?,?,?,?,?)",
        (
            request.form["name"],
            request.form["email"],
            request.form["phone"],
            request.form.get("address", ""),
            request.form.get("notes", ""),
            donation_amount,
            contact_type,
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("contacts"))


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    conn = get_connection()
    contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    if contact is None:
        conn.close()
        abort(404)
    interactions = conn.execute(
        "SELECT * FROM interactions WHERE contact_id = ? ORDER BY interaction_date DESC",
        (contact_id,),
    ).fetchall()
    conn.close()
    return render_template("contact_detail.html", contact=contact,
                           interactions=interactions, org_name=get_org_name())


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def edit_contact(contact_id):
    conn = get_connection()
    contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    if contact is None:
        conn.close()
        abort(404)
    if request.method == "POST":
        contact_type    = request.form["contact_type"]
        donation_amount = float(request.form["donation_amount"]) if contact_type == "donor" else 0.0
        conn.execute(
            "UPDATE contacts SET name=?,email=?,phone=?,address=?,notes=?,donation_amount=?,contact_type=? WHERE id=?",
            (
                request.form["name"],
                request.form["email"],
                request.form["phone"],
                request.form.get("address", ""),
                request.form.get("notes", ""),
                donation_amount,
                contact_type,
                contact_id,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("contact_detail", contact_id=contact_id))
    conn.close()
    return render_template("contact_edit.html", contact=contact, org_name=get_org_name())


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    conn = get_connection()
    conn.execute("DELETE FROM interactions WHERE contact_id = ?", (contact_id,))
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("contacts"))


@app.route("/contacts/<int:contact_id>/log", methods=["POST"])
def log_interaction(contact_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO interactions (contact_id, description, interaction_date) VALUES (?,?,?)",
        (contact_id, request.form["description"], request.form["interaction_date"]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("contact_detail", contact_id=contact_id))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    conn = get_connection()
    all_contacts = conn.execute("SELECT * FROM contacts").fetchall()
    needs_follow_up = []
    cutoff = datetime.now() - timedelta(days=FOLLOW_UP_THRESHOLD_DAYS)
    for c in all_contacts:
        last = conn.execute(
            "SELECT MAX(interaction_date) as last_date FROM interactions WHERE contact_id = ?",
            (c["id"],),
        ).fetchone()
        last_date_str = last["last_date"]
        if last_date_str is None:
            needs_follow_up.append({"contact": c, "last_date": "Never"})
        else:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            if last_date < cutoff:
                days_ago = (datetime.now() - last_date).days
                needs_follow_up.append({"contact": c, "last_date": f"{days_ago} days ago"})
    conn.close()
    return render_template("dashboard.html", needs_follow_up=needs_follow_up, org_name=get_org_name())


# ── Thank-you note ────────────────────────────────────────────────────────────

@app.route("/contacts/<int:contact_id>/thank-you")
def thank_you(contact_id):
    conn = get_connection()
    contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    latest  = conn.execute(
        "SELECT * FROM interactions WHERE contact_id = ? ORDER BY interaction_date DESC LIMIT 1",
        (contact_id,),
    ).fetchone()
    conn.close()
    org_name = get_org_name()
    note = _build_note(contact, latest, org_name)
    return render_template("thank_you.html", contact=contact, note=note, org_name=org_name)


def _build_note(contact, latest, org_name):
    first_name = contact["name"].split()[0]
    what = latest["description"] if latest else "being part of our community"
    if contact["contact_type"] == "donor":
        amount = contact["donation_amount"] or 0
        amount_str = f"${amount:,.2f}" if amount > 0 else ""
        closing = (f"Your generous donation of {amount_str} directly fuels the work we do."
                   if amount_str else "Your generosity directly fuels the work we do.")
    else:
        closing = "Volunteers like you are the heart of everything we do."
    return (
        f"Dear {first_name},\n\n"
        f"Thank you so much for {what.lower()}. "
        f"We are incredibly grateful for your support. {closing}\n\n"
        f"With gratitude,\n{org_name}"
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
