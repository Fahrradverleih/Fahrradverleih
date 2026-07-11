from flask import Flask, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime

app = Flask(__name__)

# -------------------- CONFIG --------------------

app.config['SECRET_KEY'] = 'geheimer_schluessel'

# Render Postgres Fix
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USERNAME = "chef"
ADMIN_PASSWORD = "geheim123"

PUBLIC_URL = "https://fahrradverleih.onrender.com"

# -------------------- MODELS --------------------

class Fahrrad(db.Model):
    __tablename__ = 'fahrrad'
    id = db.Column(db.Integer, primary_key=True)
    interne_nummer = db.Column(db.String(20), unique=True, nullable=False)
    marke = db.Column(db.String(50), nullable=False)
    modell = db.Column(db.String(50), nullable=False)
    rahmengroesse = db.Column(db.String(10))
    farbe = db.Column(db.String(20))
    rahmennummer = db.Column(db.String(30))
    standort = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Verfügbar')
    notizen = db.Column(db.Text)

class Kunde(db.Model):
    __tablename__ = 'kunde'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    plz_ort = db.Column(db.String(100), nullable=False)
    ausweis = db.Column(db.String(50), nullable=False)
    einwilligung_dsgvo = db.Column(db.Boolean, default=False)
    einwilligung_datum = db.Column(db.DateTime)
    haftungsausschluss_akzeptiert = db.Column(db.Boolean, default=False)
    widerrufen_am = db.Column(db.DateTime, nullable=True)
    fahrrad_id = db.Column(db.Integer, db.ForeignKey('fahrrad.id'))
    buchungs_datum = db.Column(db.DateTime, default=datetime.utcnow)

class Reservierung(db.Model):
    __tablename__ = 'reservierung'
    id = db.Column(db.Integer, primary_key=True)
    fahrrad_id = db.Column(db.Integer, db.ForeignKey('fahrrad.id'))
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'))
    reserviert_am = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Aktiv')

class Wartung(db.Model):
    __tablename__ = 'wartung'
    id = db.Column(db.Integer, primary_key=True)
    fahrrad_id = db.Column(db.Integer, db.ForeignKey('fahrrad.id'))
    mitarbeiter = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Offen')
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    erledigt_am = db.Column(db.DateTime, nullable=True)

# -------------------- LOGIN --------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("mitarbeiter"))
        return "<h3 style='color:red;'>❌ Falscher Login</h3><a href='/login'>Zurück</a>"
    return """
    <h2>Mitarbeiter Login</h2>
    <form method="POST">
        <input name="username" placeholder="Benutzername">
        <input name="password" type="password" placeholder="Passwort">
        <button>Login</button>
    </form>
    """

@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("kundenansicht"))

# -------------------- KUNDENANSICHT --------------------

@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()

    html = """
    <!DOCTYPE html>
    <html><head><title>Fahrradverleih</title></head><body>
    <h1>🚲 Fahrradverleih</h1>
    <div style='display:flex;gap:20px;flex-wrap:wrap;'>
    """

    for rad in raeder:
        html += f"<div style='border:1px solid #ccc;padding:15px;width:300px;'>"
        html += f"<h3>{rad.marke} {rad.modell}</h3>"
        html += f"<p>Nr: {rad.interne_nummer}<br>Standort: {rad.standort}</p>"
        html += f"<p>Status: <strong>{rad.status}</strong></p>"

        if rad.status == "Verfügbar":
            html += f"""
            <form method="POST" action="/reservieren/{rad.id}">
                <input name="kunde" placeholder="Name" required><br>
                <input name="email" placeholder="Email" required><br>
                <input name="adresse" placeholder="Adresse" required><br>
                <input name="plz_ort" placeholder="PLZ Ort" required><br>
                <input name="ausweis" placeholder="Ausweisnummer" required><br>
                <label><input type="checkbox" name="dsgvo" required> DSGVO akzeptiert</label><br>
                <label><input type="checkbox" name="haftung" required> Haftung akzeptiert</label><br>
                <button>Reservieren</button>
            </form>
            """
        else:
            html += "<p>🔒 Nicht verfügbar</p>"

        html += "</div>"

    html += "</div></body></html>"
    return html

# -------------------- RESERVIERUNG --------------------

@app.route('/reservieren/<int:id>', methods=['POST'])
def reservieren(id):
    rad = Fahrrad.query.get(id)
    if not rad or rad.status != "Verfügbar":
        return redirect(url_for("kundenansicht"))

    if request.form.get("dsgvo") != "on":
        return "❌ DSGVO nicht akzeptiert", 400
    if request.form.get("haftung") != "on":
        return "❌ Haftung nicht akzeptiert", 400

    kunde = Kunde(
        name=request.form["kunde"],
        email=request.form["email"],
        adresse=request.form["adresse"],
        plz_ort=request.form["plz_ort"],
        ausweis=request.form["ausweis"],
        einwilligung_dsgvo=True,
        einwilligung_datum=datetime.utcnow(),
        haftungsausschluss_akzeptiert=True,
        fahrrad_id=id
    )
    db.session.add(kunde)
    db.session.flush()

    reserv = Reservierung(fahrrad_id=id, kunde_id=kunde.id)
    db.session.add(reserv)

    rad.status = "Reserviert"
    db.session.commit()

    return redirect(url_for("kundenansicht"))

# -------------------- WIDERRUF --------------------

@app.route('/widerruf', methods=['GET', 'POST'])
def widerruf():
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            return "Bitte Email eingeben", 400

        kunden = Kunde.query.filter_by(email=email, einwilligung_dsgvo=True).all()
        if not kunden:
            return "<h3>❌ Keine Einwilligung gefunden</h3>"

        for k in kunden:
            k.einwilligung_dsgvo = False
            k.widerrufen_am = datetime.utcnow()
            k.name = "[Anonymisiert]"
            k.adresse = "[Anonymisiert]"
            k.plz_ort = "[Anonymisiert]"
            k.ausweis = "[Anonymisiert]"

        db.session.commit()
        return "<h3>✅ Einwilligung widerrufen</h3><a href='/'>Zurück</a>"

    return """
    <h2>Einwilligung widerrufen</h2>
    <form method="POST">
        <input name="email" placeholder="Email">
        <button>Widerrufen</button>
    </form>
    """

# -------------------- QR CODE --------------------

@app.route('/qr/<int:id>')
def qr_code(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404

    qr = qrcode.make(f"{PUBLIC_URL}/rad/{id}")
    buf = BytesIO()
    qr.save(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return f"<img src='data:image/png;base64,{img_b64}'>"

# -------------------- MITARBEITER DASHBOARD --------------------

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()

    html = """
    <h1>🔧 Mitarbeiter Dashboard</h1>
    <a href="/logout">Logout</a>
    <h2>Fahrräder</h2>
    <table border="1">
    <tr><th>Nr</th><th>Marke</th><th>Modell</th><th>Status</th><th>Aktionen</th></tr>
    """

    for r in raeder:
        html += f"""
        <tr>
            <td>{r.interne_nummer}</td>
            <td>{r.marke}</td>
            <td>{r.modell}</td>
            <td>{r.status}</td>
            <td>
                <a href="/qr/{r.id}">QR</a>
                <a href="/mitarbeiter/delete/{r.id}">Löschen</a>
            </td>
        </tr>
        """

    html += "</table>"

    html += "<h2>Kunden</h2><table border='1'><tr><th>Name</th><th>Email</th></tr>"
    for k in kunden:
        html += f"<tr><td>{k.name}</td><td>{k.email}</td></tr>"
    html += "</table>"

    return html

# -------------------- DELETE BIKE --------------------

@app.route('/mitarbeiter/delete/<int:id>')
@login_required
def delete_bike(id):
    rad = Fahrrad.query.get(id)
    if rad:
        db.session.delete(rad)
        db.session.commit()
    return redirect(url_for("mitarbeiter"))

# -------------------- START --------------------

if __name__ == "__main__":
    app.run(debug=True)
