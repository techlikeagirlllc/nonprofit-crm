# NonProfit CRM

A lightweight contact relationship manager built for nonprofits. Track donors and volunteers, log interactions, flag overdue follow-ups, and send personalized thank-you notes — all from a simple web interface that runs on your own server.

Designed by **TechLikeAGirl** · Powered by **Claude**

**Live demo:** https://nonprofit-crm.onrender.com

---

## What It Does

- **Contacts** — Store donors and volunteers with name, email, phone, address, donation amount, and notes
- **Interaction Log** — Record every touchpoint (calls, events, donations) against a contact
- **Follow-Up Dashboard** — Automatically surfaces anyone you haven't contacted in 30+ days
- **Thank-You Notes** — Auto-drafts a personalized email based on the contact's latest interaction and opens it in your mail app ready to send
- **Search** — Live search across all contacts by name, email, phone, or type
- **Password Protected** — Each installation is secured with a password you set on first run

---

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

No database server, no cloud account, no paid services required.

---

## Installation

**1. Download the project**

Place the `Non-ProfitCRM` folder anywhere on your computer or server.

**2. Open a terminal in that folder and install dependencies**

```bash
pip install -r requirements.txt
```

**3. Start the app**

```bash
python app.py
```

**4. Open your browser and go to:**

```
http://127.0.0.1:5000
```

You will be greeted by a one-time setup screen. Enter your organization's name and choose a password. That's it — your CRM is ready to use.

---

## First-Time Setup

The first time you visit the app you will see a setup screen asking for:

- **Organization Name** — shown throughout the app (e.g. *Riverside Food Bank*)
- **Password** — used to log in on every visit (minimum 8 characters)

This information is saved to `config.json` in the project folder. You will not see the setup screen again unless you delete that file.

---

## Your Data

All data is stored locally in two files:

| File | Contents |
|---|---|
| `crm.db` | All contacts and interaction history |
| `config.json` | Your organization name and password |

**To back up your data**, copy these two files somewhere safe. To restore, put them back in the project folder.

---

## Deploying for Multiple Nonprofits

Each nonprofit gets their own independent installation on their own server. There is no shared data between installations. To set up a new nonprofit:

1. Copy the project folder to their server
2. Run `pip install -r requirements.txt`
3. Run `python app.py`
4. Visit the app — the setup screen will appear for them to enter their org name and password

---

## Running on a Server (Production)

The default `python app.py` command is fine for local use. For a server that others will access over the internet:

**1. Install Gunicorn**
```bash
pip install gunicorn
```

**2. Run with Gunicorn**
```bash
gunicorn app:app --bind 0.0.0.0:5000
```

**3. Add HTTPS**

Use [Certbot](https://certbot.eff.org/) with Nginx to get a free SSL certificate so passwords are never sent in plain text.

---

## Changing Your Password or Org Name

Open `config.json` in a text editor. You can update `org_name` directly. To change the password, delete the `password_hash` line and restart the app — the setup screen will reappear and let you set a new one.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| Database | SQLite |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Password hashing | Werkzeug (bcrypt) |

---

Designed by **TechLikeAGirl** · Powered by **Claude**
