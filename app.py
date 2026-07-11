from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime

app = Flask(__name__)

# ==================== SICHERHEIT ====================

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "fallback_key")

# ==================== DATABASE FIX FÜR RENDER ====================

db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== LOGIN KONFIGURATION ====================

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "chef")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "geheim123")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('mitarbeiter'))
        else:
            return """
            <!DOCTYPE html>
            <html>
            <head><title>Login Fehler</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; width: 320px; }
                .error { color: red; font-weight: bold; }
                .btn { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; }
            </style>
            </head>
            <body>
            <div class="box">
                <h3 class="error">❌ Falscher Name oder Passwort!</h3>
                <a href="/login" class="btn">Nochmal versuchen</a>
            </div>
            </body>
            </html>
            """

    return """
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; width: 320px; }
        .logo { font-size: 3rem; margin-bottom: 10px; }
        input { width: 90%; padding: 12px; margin: 10px 0; border: 2px solid #e5e7eb; border-radius: 8px; font-size: 1rem; }
        input:focus { border-color: #667eea; outline: none; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 1rem; font-weight: 600; }
        .btn:hover { transform: scale(1.02); }
    </style>
    </head>
    <body>
    <div class="box">
        <div class="logo">🚲</div>
        <h2>Mitarbeiter Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Benutzername" required>
            <input type="password" name="password" placeholder="Passwort" required>
            <button type="submit" class="btn">Einloggen</button>
        </form>
    </div>
    </body>
    </html>
    """

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('kundenansicht'))

# ==================== FEHLENDE ROUTEN HINZUGEFÜGT ====================

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    return "<h1>Mitarbeiterbereich</h1>"

@app.route('/kundenansicht')
def kundenansicht():
    return "<h1>Kundenansicht</h1>"

# ==================== PUBLIC URL ====================

PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://fahrradverleih.onrender.com")
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Sichere ENV-Variablen statt Klartext
        admin_user = os.environ.get("ADMIN_USERNAME", ADMIN_USERNAME)
        admin_pass = os.environ.get("ADMIN_PASSWORD", ADMIN_PASSWORD)

        if username == admin_user and password == admin_pass:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('mitarbeiter'))
        else:
            return """
            <h3 style='color:red;'>❌ Falscher Name oder Passwort!</h3>
            <a href='/login'>Nochmal versuchen</a>
            """

    # Login-Formular
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
               height: 100vh; background: linear-gradient(135deg,#667eea,#764ba2); }
        .box { background: white; padding: 40px; border-radius: 12px;
               box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; width: 320px; }
        .logo { font-size: 3rem; margin-bottom: 10px; }
        input { width: 90%; padding: 12px; margin: 10px 0; border: 2px solid #e5e7eb;
                border-radius: 8px; font-size: 1rem; }
        input:focus { border-color: #667eea; outline: none; }
        .btn { background: linear-gradient(135deg,#667eea,#764ba2); color: white; border: none;
               padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 1rem; font-weight: 600; }
        .btn:hover { transform: scale(1.02); }
    </style>
    </head>
    <body>
    <div class="box">
        <div class="logo">🚲</div>
        <h2>Mitarbeiter Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Benutzername" required>
            <input type="password" name="password" placeholder="Passwort" required>
            <button type="submit" class="btn">Einloggen</button>
        </form>
    </div>
    </body>
    </html>
    """


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('kundenansicht'))
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Sichere ENV-Variablen statt Klartext
        admin_user = os.environ.get("ADMIN_USERNAME", ADMIN_USERNAME)
        admin_pass = os.environ.get("ADMIN_PASSWORD", ADMIN_PASSWORD)

        if username == admin_user and password == admin_pass:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('mitarbeiter'))
        else:
            return """
            <h3 style='color:red;'>❌ Falscher Name oder Passwort!</h3>
            <a href='/login'>Nochmal versuchen</a>
            """

    # Login-Formular
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
               height: 100vh; background: linear-gradient(135deg,#667eea,#764ba2); }
        .box { background: white; padding: 40px; border-radius: 12px;
               box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; width: 320px; }
        .logo { font-size: 3rem; margin-bottom: 10px; }
        input { width: 90%; padding: 12px; margin: 10px 0; border: 2px solid #e5e7eb;
                border-radius: 8px; font-size: 1rem; }
        input:focus { border-color: #667eea; outline: none; }
        .btn { background: linear-gradient(135deg,#667eea,#764ba2); color: white; border: none;
               padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 1rem; font-weight: 600; }
        .btn:hover { transform: scale(1.02); }
    </style>
    </head>
    <body>
    <div class="box">
        <div class="logo">🚲</div>
        <h2>Mitarbeiter Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Benutzername" required>
            <input type="password" name="password" placeholder="Passwort" required>
            <button type="submit" class="btn">Einloggen</button>
        </form>
    </div>
    </body>
    </html>
    """


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('kundenansicht'))
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Sichere ENV-Variablen statt Klartext
        admin_user = os.environ.get("ADMIN_USERNAME", ADMIN_USERNAME)
        admin_pass = os.environ.get("ADMIN_PASSWORD", ADMIN_PASSWORD)

        if username == admin_user and password == admin_pass:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('mitarbeiter'))
        else:
            return """
            <h3 style='color:red;'>❌ Falscher Name oder Passwort!</h3>
            <a href='/login'>Nochmal versuchen</a>
            """

    # Login-Formular
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
               height: 100vh; background: linear-gradient(135deg,#667eea,#764ba2); }
        .box { background: white; padding: 40px; border-radius: 12px;
               box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; width: 320px; }
        .logo { font-size: 3rem; margin-bottom: 10px; }
        input { width: 90%; padding: 12px; margin: 10px 0; border: 2px solid #e5e7eb;
                border-radius: 8px; font-size: 1rem; }
        input:focus { border-color: #667eea; outline: none; }
        .btn { background: linear-gradient(135deg,#667eea,#764ba2); color: white; border: none;
               padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 1rem; font-weight: 600; }
        .btn:hover { transform: scale(1.02); }
    </style>
    </head>
    <body>
    <div class="box">
        <div class="logo">🚲</div>
        <h2>Mitarbeiter Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Benutzername" required>
            <input type="password" name="password" placeholder="Passwort" required>
            <button type="submit" class="btn">Einloggen</button>
        </form>
    </div>
    </body>
    </html>
    """


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('kundenansicht'))
@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🚲 Fahrradverleih</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f8fafc; padding: 20px; }
            .header { background: linear-gradient(135deg,#2563eb,#7c3aed); color:white;
                      padding:30px 20px; border-radius:16px; margin-bottom:30px;
                      display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }
            .header h1 { font-size:2rem; display:flex; align-items:center; gap:10px; }
            .sub { font-size:0.9rem; opacity:0.9; }
            .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(380px,1fr)); gap:24px; }
            .card { background:white; padding:24px; border-radius:16px;
                    box-shadow:0 4px 12px rgba(0,0,0,0.06); transition:0.2s; }
            .card:hover { transform:translateY(-4px); box-shadow:0 8px 24px rgba(0,0,0,0.1); }
            .badge { padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:700; }
            .verfuegbar { background:#dcfce7; color:#166534; }
            .reserviert { background:#fef3c7; color:#92400e; }
            .wartung { background:#fee2e2; color:#991b1b; }
        </style>
    </head>
    <body>

    <div class="header">
        <div>
            <h1>🚲 Fahrradverleih</h1>
            <div class="sub">📍 Dein zuverlässiger Partner für Fahrradmiete</div>
        </div>
        <div class="logo-img">⭐ 4.8</div>
    </div>

    <div class="grid">
    """

    # Fahrräder rendern
    for r in raeder:
        status_class = "verfuegbar"
        if r.status == "Reserviert":
            status_class = "reserviert"
        elif r.status == "Wartung":
            status_class = "wartung"

        html += f"""
        <div class="card">
            <h3>{r.marke} {r.modell}</h3>
            <p><strong>Interne Nummer:</strong> {r.interne_nummer}</p>
            <p><strong>Rahmengröße:</strong> {r.rahmengroesse or '–'}</p>
            <p><strong>Farbe:</strong> {r.farbe or '–'}</p>
            <p><strong>Standort:</strong> {r.standort or '–'}</p>
            <span class="badge {status_class}">{r.status}</span>
        </div>
        """

    html += "</div></body></html>"
    return html
# DSGVO‑Modal
html += """
<div id="dsgvoModal" class="modal">
    <div class="modal-content">
        <button class="modal-close" onclick="document.getElementById('dsgvoModal').style.display='none'">✕</button>
        <h2>📄 Datenschutzerklärung (DSGVO)</h2><hr>
        <p><strong>Verantwortlicher:</strong> Fahrradverleih GmbH, Musterstraße 1, 12345 Berlin</p>
        <p><strong>Zweck:</strong> Ihre Daten werden zur Abwicklung der Fahrradvermietung erhoben.</p>
        <p><strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) und Art. 6 Abs. 1 lit. a DSGVO (Einwilligung).</p>
        <p><strong>Speicherdauer:</strong> 7 Tage nach Rückgabe, dann Löschung.</p>
        <p><strong>Weitergabe:</strong> Keine Weitergabe an Dritte.</p>
        <p><strong>Ihre Rechte:</strong> Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung und Datenübertragbarkeit.
            Kontakt: <a href="mailto:datenschutz@fahrradverleih.de">datenschutz@fahrradverleih.de</a>
        </p>
        <p><strong>Widerruf:</strong> Jederzeit <a href="/widerruf" target="_blank">hier</a> möglich.</p>
        <p><small>Stand: Juli 2026</small></p>
    </div>
</div>
"""

# Haftung‑Modal
html += """
<div id="haftungModal" class="modal">
    <div class="modal-content">
        <button class="modal-close" onclick="document.getElementById('haftungModal').style.display='none'">✕</button>
        <h2>⚠️ Haftungsausschluss</h2><hr>
        <p><strong>1. Nutzung auf eigene Gefahr</strong><br>Die Nutzung der Fahrräder erfolgt ausschließlich auf eigene Gefahr.</p>
        <p><strong>2. Haftungsfreistellung</strong><br>Der Mieter stellt den Verleiher von allen Ansprüchen Dritter frei.</p>
        <p><strong>3. Eigenverantwortung</strong><br>Der Mieter prüft das Fahrrad vor Fahrtantritt auf Verkehrssicherheit.</p>
        <p><strong>4. Versicherung</strong><br>Der Mieter sollte eine eigene Haftpflichtversicherung besitzen.</p>
        <p><strong>5. Unfälle</strong><br>Bei Unfällen haftet der Mieter selbst.</p>
        <p><small>Stand: Juli 2026</small></p>
    </div>
</div>
"""

# Fahrrad‑Grid
html += '<div class="grid">'

for rad in raeder:
    status_class = (rad.status or "Verfügbar").lower()

    html += f"""
    <div class="card">
        <h3>🚲 {rad.marke} {rad.modell}</h3>
        <p>
            <strong>Nr:</strong> {rad.interne_nummer}<br>
            <strong>Größe:</strong> {rad.rahmengroesse or '–'} / {rad.farbe or '–'}<br>
            <strong>Standort:</strong> {rad.standort or '–'}
        </p>
        <span class="badge {status_class}">{rad.status}</span><br><br>
    """

    if rad.status == "Verfügbar":
        html += f"""
        <form action="/reservieren/{rad.id}" method="POST" onsubmit="return validateForm(this)">
            <input type="text" name="kunde" placeholder="Vor- und Nachname *" required class="full-width">

            <div class="form-grid">
                <input type="email" name="email" placeholder="E-Mail *" required>
                <input type="text" name="ausweis" placeholder="Ausweis-Nr. *" required>
                <input type="text" name="adresse" placeholder="Straße & Hausnr. *" required class="full-width">
                <input type="text" name="plz_ort" placeholder="PLZ & Ort *" required class="full-width">
            </div>

            <div class="checkbox-group">
                <input type="checkbox" id="dsgvo_{rad.id}" name="dsgvo" required>
                <label for="dsgvo_{rad.id}">
                    Ich habe die <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">Datenschutzerklärung</span> gelesen und stimme zu.
                </label>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" id="haftung_{rad.id}" name="haftung" required>
                <label for="haftung_{rad.id}">
                    Ich akzeptiere den <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">Haftungsausschluss</span>.
                </label>
            </div>

            <div class="warning-box">
                ⚠️ <strong>Wichtig:</strong> Sie bestätigen die Prüfung auf Verkehrssicherheit.
            </div>

            <button type="submit" class="btn">✅ Jetzt verbindlich reservieren</button>
        </form>
        """
    else:
        html += '<p style="color:#94a3b8;font-style:italic;">🔒 Aktuell nicht verfügbar</p>'

    html += "</div>"

html += "</div>"

# Footer
html += """
<div class="footer">
    <a href="/widerruf" target="_blank">🔒 Einwilligung widerrufen</a>
    <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">📄 Datenschutzerklärung</span>
    <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">⚠️ Haftungsausschluss</span>
    <a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter-Login</a>
</div>
"""

# JS
html += """
<script>
function validateForm(form) {
    if (!form.dsgvo.checked) { alert('Bitte stimmen Sie der Datenschutzerklärung zu.'); return false; }
    if (!form.haftung.checked) { alert('Bitte akzeptieren Sie den Haftungsausschluss.'); return false; }
    return true;
}

window.onclick = function(event) {
    const dsgvoModal = document.getElementById('dsgvoModal');
    const haftungModal = document.getElementById('haftungModal');
    if (event.target === dsgvoModal) dsgvoModal.style.display = 'none';
    if (event.target === haftungModal) haftungModal.style.display = 'none';
}
</script>
"""

html += "</body></html>"
return html
@app.route('/widerruf', methods=['GET', 'POST'])
def widerruf():
    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            return "Bitte E-Mail angeben.", 400

        # Nur Kunden mit aktiver Einwilligung
        kunden = Kunde.query.filter_by(email=email, einwilligung_dsgvo=True).all()

        if not kunden:
            return "<h2>❌ Keine Einwilligung gefunden.</h2><a href='/widerruf'>Zurück</a>"

        # DSGVO-konforme Anonymisierung
        for kunde in kunden:
            kunde.einwilligung_dsgvo = False
            kunde.widerrufen_am = datetime.utcnow()
            kunde.name = "[Anonymisiert]"
            kunde.adresse = "[Anonymisiert]"
            kunde.plz_ort = "[Anonymisiert]"
            kunde.ausweis = "[Anonymisiert]"

        db.session.commit()

        return "<h2>✅ Einwilligung erfolgreich widerrufen</h2><a href='/'>Zurück</a>"

    # GET: Formular anzeigen
    return """
    <h2>🔒 Einwilligung widerrufen</h2>
    <p>Geben Sie Ihre E-Mail ein:</p>
    <form method="POST">
        <input type="email" name="email" required>
        <button type="submit">Widerrufen</button>
    </form>
    <br><a href="/">Zurück</a>
    """
@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    wartungen = Wartung.query.all()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mitarbeiter</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background:#f8fafc; padding:20px; }
            .header { background:linear-gradient(135deg,#1e293b,#0f172a); color:white;
                      padding:20px; border-radius:12px; margin-bottom:20px;
                      display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; }
            .btn-logout { background:#ef4444; color:white; padding:8px 16px; border-radius:8px;
                          text-decoration:none; font-weight:600; }
            .btn-logout:hover { background:#dc2626; }
            .tab { display:inline-block; padding:10px 20px; cursor:pointer; background:#e2e8f0;
                   border-radius:8px 8px 0 0; margin-right:4px; font-weight:600; }
            .tab.active { background:white; color:#2563eb; }
            .tab-content { display:none; background:white; padding:20px; border-radius:0 8px 8px 8px;
                           border:1px solid #e2e8f0; }
            .tab-content.active { display:block; }
            table { width:100%; border-collapse:collapse; margin-top:20px; }
            th, td { border:1px solid #e2e8f0; padding:10px; text-align:left; }
            th { background:#f1f5f9; font-weight:700; }
            .btn { padding:5px 12px; border:none; border-radius:6px; cursor:pointer;
                   text-decoration:none; color:white; display:inline-block; font-size:0.8rem; font-weight:600; }
            .btn-edit { background:#2563eb; }
            .btn-del { background:#ef4444; }
            .btn-qr { background:#000; }
            .btn-add { background:#16a34a; }
            .btn-wartung { background:#f59e0b; }
            .badge { padding:2px 10px; border-radius:12px; font-size:0.7rem; font-weight:700; display:inline-block; }
            .verfuegbar { background:#dcfce7; color:#166534; }
            .reserviert { background:#fef3c7; color:#92400e; }
            .wartung { background:#fee2e2; color:#991b1b; }
            .offen { background:#fee2e2; color:#991b1b; }
            .inbearbeitung { background:#fef3c7; color:#92400e; }
            .erledigt { background:#dcfce7; color:#166534; }
        </style>
    </head>
    <body>

    <div class="header">
        <h1>🔧 Mitarbeiter Dashboard</h1>
        <a href="/logout" class="btn-logout">Logout</a>
    </div>

    <a href="/">← Zurück zur Kundenansicht</a><br><br>

    <div class="tab active" onclick="showTab('fahrraeder')">🚲 Fahrräder</div>
    <div class="tab" onclick="showTab('kunden')">👤 Kunden ({})</div>
    <div class="tab" onclick="showTab('wartungen')">🔧 Wartungen ({})</div>
    """.format(len(kunden), len(wartungen))

    # ------------------ TAB: FAHRRÄDER ------------------
    html += """
    <div id="tab-fahrraeder" class="tab-content active">
        <div class="form-box">
            <h3>➕ Neues Fahrrad anlegen</h3>
            <form action="/mitarbeiter/add" method="POST">
                Nr: <input type="text" name="interne_nummer" required>
                Marke: <input type="text" name="marke" required>
                Modell: <input type="text" name="modell" required>
                Größe: <input type="text" name="rahmengroesse">
                Farbe: <input type="text" name="farbe">
                Standort: <input type="text" name="standort">
                <button type="submit" class="btn btn-add">Hinzufügen</button>
            </form>
        </div>

        <h3>📋 Alle Fahrräder</h3>
        <table>
            <tr><th>Nr</th><th>Marke</th><th>Modell</th><th>Status</th><th>Standort</th><th>Aktionen</th></tr>
    """

    for rad in raeder:
        status_class = (rad.status or "Verfügbar").lower()
        html += f"""
            <tr>
                <td>{rad.interne_nummer}</td>
                <td>{rad.marke}</td>
                <td>{rad.modell}</td>
                <td><span class="badge {status_class}">{rad.status}</span></td>
                <td>{rad.standort}</td>
                <td>
                    <a href="/qr/{rad.id}" class="btn btn-qr" target="_blank">QR</a>
                    <a href="/rad/{rad.id}" class="btn btn-wartung">Historie</a>
                    <a href="/mitarbeiter/delete/{rad.id}" class="btn btn-del" onclick="return confirm('Sicher löschen?')">Löschen</a>
                </td>
            </tr>
        """

    html += "</table></div>"

    # ------------------ TAB: KUNDEN ------------------
    html += """
    <div id="tab-kunden" class="tab-content">
        <h3>👤 Kunden mit Einwilligung</h3>
        <table>
            <tr><th>Name</th><th>Email</th><th>Adresse</th><th>DSGVO</th><th>Haftung</th><th>Datum</th></tr>
    """

    for k in kunden:
        datum = k.einwilligung_datum.strftime("%d.%m.%Y %H:%M") if k.einwilligung_datum else "-"
        html += f"""
            <tr>
                <td>{k.name}</td>
                <td>{k.email}</td>
                <td>{k.adresse}, {k.plz_ort}</td>
                <td>{"✅" if k.einwilligung_dsgvo else "❌"}</td>
                <td>{"✅" if k.haftungsausschluss_akzeptiert else "❌"}</td>
                <td>{datum}</td>
            </tr>
        """

    html += "</table></div>"

    # ------------------ TAB: WARTUNGEN ------------------
    html += """
    <div id="tab-wartungen" class="tab-content">
        <h3>🔧 Alle Wartungen</h3>
        <table>
            <tr><th>Fahrrad</th><th>Mitarbeiter</th><th>Problem</th><th>Status</th><th>Datum</th><th>Aktionen</th></tr>
    """

    for w in wartungen:
        status_class = "offen" if w.status == "Offen" else "inbearbeitung" if w.status == "In Bearbeitung" else "erledigt"
        problem_text = w.problem[:50] + ("..." if len(w.problem) > 50 else "")
        datum = w.erstellt_am.strftime("%d.%m.%Y %H:%M")

        html += f"""
            <tr>
                <td>{w.fahrrad_id}</td>
                <td>{w.mitarbeiter}</td>
                <td>{problem_text}</td>
                <td><span class="badge {status_class}">{w.status}</span></td>
                <td>{datum}</td>
                <td>
                    <a href="/wartung/{w.id}/edit" class="btn btn-edit">Bearbeiten</a>
                    <a href="/wartung/{w.id}/delete" class="btn btn-del" onclick="return confirm('Wartung löschen?')">Löschen</a>
                </td>
            </tr>
        """

    html += "</table></div>"

    # ------------------ JS ------------------
    html += """
    <script>
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector('[onclick="showTab(\\'' + tab + '\\')"]').classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
    </script>
    </body></html>
    """

    return html
