from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = 'dein_geheimer_schluessel_hier_12345!'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USERNAME = "chef"
ADMIN_PASSWORD = "geheim123"

PUBLIC_URL = os.environ.get('PUBLIC_URL', 'https://fahrradverleih.onrender.com')

# ==================== DATENBANK-MODELLE ====================

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

# ====== NEU: Wartungs-Log für Mitarbeiter ======
class Wartung(db.Model):
    __tablename__ = 'wartung'
    id = db.Column(db.Integer, primary_key=True)
    fahrrad_id = db.Column(db.Integer, db.ForeignKey('fahrrad.id'))
    mitarbeiter = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Offen')
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    erledigt_am = db.Column(db.DateTime, nullable=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== LOGIN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('mitarbeiter'))
        else:
            return "<h3 style='color:red;'>Falscher Name oder Passwort!</h3><a href='/login'>Nochmal versuchen</a>"
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

# ==================== KUNDENANSICHT ====================

HTML_KUNDEN = """
<!DOCTYPE html>
<html>
<head>
    <title>🚲 Fahrradverleih</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; padding: 20px; }
        .header { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; padding: 30px 20px; border-radius: 16px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .header h1 { font-size: 2rem; display: flex; align-items: center; gap: 10px; }
        .header .sub { font-size: 0.9rem; opacity: 0.9; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 24px; }
        .card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); transition: transform 0.2s; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
        .card h3 { font-size: 1.3rem; color: #1e293b; margin-bottom: 8px; }
        .card p { color: #64748b; margin: 4px 0; }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; text-transform: uppercase; }
        .verfuegbar { background: #dcfce7; color: #166534; }
        .reserviert { background: #fef3c7; color: #92400e; }
        .wartung { background: #fee2e2; color: #991b1b; }
        .btn { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: 700; font-size: 1rem; transition: transform 0.2s; }
        .btn:hover { transform: scale(1.02); }
        input { width: 100%; padding: 10px 12px; border: 2px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px; font-size: 0.95rem; }
        input:focus { border-color: #2563eb; outline: none; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .full-width { grid-column: span 2; }
        .checkbox-group { display: flex; align-items: flex-start; gap: 10px; margin: 10px 0; font-size: 0.85rem; color: #334155; }
        .checkbox-group input { width: 18px; height: 18px; margin-top: 2px; accent-color: #2563eb; }
        .checkbox-group label { line-height: 1.4; }
        .ds-link { color: #2563eb; cursor: pointer; text-decoration: underline; font-weight: 600; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; padding: 20px; }
        .modal-content { background: white; padding: 30px; border-radius: 16px; max-width: 600px; max-height: 80vh; overflow-y: auto; }
        .modal-close { float: right; background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 20px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }
        .footer a { color: #2563eb; text-decoration: none; font-weight: 600; }
        .footer a:hover { color: #7c3aed; text-decoration: underline; }
        .warning-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 10px 0; font-size: 0.85rem; color: #991b1b; border-radius: 4px; }
        @media (max-width: 640px) {
            .header { flex-direction: column; text-align: center; }
            .header h1 { font-size: 1.5rem; }
            .grid { grid-template-columns: 1fr; }
            .form-grid { grid-template-columns: 1fr; }
            .full-width { grid-column: span 1; }
        }
        .logo-img { font-size: 2.5rem; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1><span>🚲</span> Fahrradverleih</h1>
            <div class="sub">📍 Dein zuverlässiger Partner für Fahrradmiete</div>
        </div>
        <div class="logo-img">⭐ 4.8</div>
    </div>
    
    <div id="dsgvoModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('dsgvoModal').style.display='none'">✕</button>
            <h2>📄 Datenschutzerklärung (DSGVO)</h2>
            <hr>
            <p><strong>Verantwortlicher:</strong> Fahrradverleih GmbH, Musterstraße 1, 12345 Berlin</p>
            <p><strong>Zweck:</strong> Ihre Daten werden zur Abwicklung der Fahrradvermietung erhoben.</p>
            <p><strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) und Art. 6 Abs. 1 lit. a DSGVO (Einwilligung).</p>
            <p><strong>Speicherdauer:</strong> 7 Tage nach Rückgabe, dann Löschung.</p>
            <p><strong>Weitergabe:</strong> Keine Weitergabe an Dritte.</p>
            <p><strong>Ihre Rechte:</strong> Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung und Datenübertragbarkeit. Kontakt: <a href="mailto:datenschutz@fahrradverleih.de">datenschutz@fahrradverleih.de</a></p>
            <p><strong>Widerruf:</strong> Jederzeit <a href="/widerruf" target="_blank">hier</a> möglich.</p>
            <p><small>Stand: Juli 2026</small></p>
        </div>
    </div>

    <div id="haftungModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('haftungModal').style.display='none'">✕</button>
            <h2>⚠️ Haftungsausschluss</h2>
            <hr>
            <p><strong>1. Nutzung auf eigene Gefahr</strong><br>Die Nutzung der Fahrräder erfolgt ausschließlich auf eigene Gefahr. Der Mieter versichert, dass er das Fahrrad sicher beherrscht und alle Verkehrsregeln kennt.</p>
            <p><strong>2. Haftungsfreistellung</strong><br>Der Mieter stellt den Verleiher von allen Ansprüchen Dritter frei, die im Zusammenhang mit der Nutzung entstehen. Der Mieter haftet für alle Schäden durch unsachgemäße Nutzung.</p>
            <p><strong>3. Eigenverantwortung</strong><br>Der Mieter ist selbst verantwortlich für die Prüfung des Fahrrads auf Verkehrssicherheit (Bremsen, Beleuchtung, Reifen) vor Fahrtantritt.</p>
            <p><strong>4. Versicherung</strong><br>Der Mieter ist angehalten, eine eigene Haftpflichtversicherung abzuschließen.</p>
            <p><strong>5. Unfälle</strong><br>Bei Unfällen oder Stürzen haftet der Mieter selbst. Der Verleiher übernimmt keine Haftung für Personen- oder Sachschäden.</p>
            <p><small>Stand: Juli 2026</small></p>
        </div>
    </div>

    <div class="grid">
        {% for rad in raeder %}
        <div class="card">
            <h3>🚲 {{ rad.marke }} {{ rad.modell }}</h3>
            <p><strong>Nr:</strong> {{ rad.interne_nummer }}<br>
            <strong>Größe:</strong> {{ rad.rahmengroesse }} / {{ rad.farbe }}<br>
            <strong>Standort:</strong> {{ rad.standort }}</p>

            <span class="badge {{ 'verfuegbar' if rad.status == 'Verfügbar' else 'reserviert' if rad.status == 'Reserviert' else 'wartung' }}">
                {{ rad.status }}
            </span>

            <br><br>
            {% if rad.status == 'Verfügbar' %}
                <form action="/reservieren/{{ rad.id }}" method="POST" onsubmit="return validateForm(this)">
                    <input type="text" name="kunde" placeholder="Vor- und Nachname *" required class="full-width">
                    <div class="form-grid">
                        <input type="email" name="email" placeholder="E-Mail *" required>
                        <input type="text" name="ausweis" placeholder="Ausweis-Nr. *" required>
                        <input type="text" name="adresse" placeholder="Straße & Hausnr. *" required class="full-width">
                        <input type="text" name="plz_ort" placeholder="PLZ & Ort *" required class="full-width">
                    </div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="dsgvo_{{ rad.id }}" name="dsgvo" required>
                        <label for="dsgvo_{{ rad.id }}">
                            Ich habe die <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">Datenschutzerklärung</span> gelesen und stimme der Speicherung meiner Daten gemäß DSGVO zu. 
                            Die Einwilligung kann jederzeit <a href="/widerruf" target="_blank">widerrufen</a> werden.
                        </label>
                    </div>

                    <div class="checkbox-group">
                        <input type="checkbox" id="haftung_{{ rad.id }}" name="haftung" required>
                        <label for="haftung_{{ rad.id }}">
                            Ich habe den <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">Haftungsausschluss</span> gelesen und akzeptiere, dass ich die volle Verantwortung für die Nutzung trage.
                        </label>
                    </div>

                    <div class="warning-box">
                        ⚠️ <strong>Wichtig:</strong> Mit der Buchung bestätigen Sie die Prüfung auf Verkehrssicherheit und die Nutzung auf eigene Gefahr.
                    </div>
                    
                    <button type="submit" class="btn">✅ Jetzt verbindlich reservieren</button>
                </form>
            {% else %}
                <p style="color: #94a3b8; font-style: italic;">🔒 Aktuell nicht verfügbar</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        <a href="/widerruf" target="_blank">🔒 Einwilligung widerrufen</a>
        <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">📄 Datenschutzerklärung</span>
        <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">⚠️ Haftungsausschluss</span>
        <a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter-Login</a>
    </div>

    <script>
        function validateForm(form) {
            const dsgvo = form.querySelector('input[name="dsgvo"]');
            if (!dsgvo.checked) {
                alert('Bitte stimmen Sie der Datenschutzerklärung zu.');
                return false;
            }
            const haftung = form.querySelector('input[name="haftung"]');
            if (!haftung.checked) {
                alert('Bitte akzeptieren Sie den Haftungsausschluss.');
                return false;
            }
            return true;
        }
        window.onclick = function(event) {
            const dsgvoModal = document.getElementById('dsgvoModal');
            const haftungModal = document.getElementById('haftungModal');
            if (event.target === dsgvoModal) {
                dsgvoModal.style.display = 'none';
            }
            if (event.target === haftungModal) {
                haftungModal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()
    return render_template_string(HTML_KUNDEN, raeder=raeder)

@app.route('/reservieren/<int:id>', methods=['POST'])
def reservieren(id):
    rad = Fahrrad.query.get(id)
    if not rad or rad.status != 'Verfügbar':
        return redirect(url_for('kundenansicht'))
    
    if request.form.get('dsgvo') != 'on':
        return "Fehler: Sie müssen der Datenschutzerklärung zustimmen.", 400
    if request.form.get('haftung') != 'on':
        return "Fehler: Sie müssen den Haftungsausschluss akzeptieren.", 400
    
    kunde = Kunde(
        name=request.form['kunde'],
        email=request.form['email'],
        adresse=request.form['adresse'],
        plz_ort=request.form['plz_ort'],
        ausweis=request.form['ausweis'],
        einwilligung_dsgvo=True,
        einwilligung_datum=datetime.utcnow(),
        haftungsausschluss_akzeptiert=True,
        fahrrad_id=rad.id
    )
    db.session.add(kunde)
    db.session.flush()
    
    reservierung = Reservierung(
        fahrrad_id=rad.id,
        kunde_id=kunde.id
    )
    db.session.add(reservierung)
    
    rad.status = 'Reserviert'
    db.session.commit()
    
    flash('✅ Reservierung erfolgreich!', 'success')
    return redirect(url_for('kundenansicht'))

@app.route('/widerruf', methods=['GET', 'POST'])
def widerruf():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            return "Bitte E-Mail angeben.", 400
        
        kunden = Kunde.query.filter_by(email=email, einwilligung_dsgvo=True).all()
        if not kunden:
            return "<h2>❌ Keine Einwilligung gefunden.</h2><a href='/widerruf'>Zurück</a>"
        
        for kunde in kunden:
            kunde.einwilligung_dsgvo = False
            kunde.widerrufen_am = datetime.utcnow()
            kunde.name = "[Anonymisiert]"
            kunde.adresse = "[Anonymisiert]"
            kunde.plz_ort = "[Anonymisiert]"
            kunde.ausweis = "[Anonymisiert]"
        db.session.commit()
        
        return "<h2>✅ Einwilligung erfolgreich widerrufen</h2><a href='/'>Zurück</a>"
    
    return """
    <h2>🔒 Einwilligung widerrufen</h2>
    <p>Geben Sie Ihre E-Mail ein:</p>
    <form method="POST">
        <input type="email" name="email" required>
        <button type="submit">Widerrufen</button>
    </form>
    <br><a href="/">Zurück</a>
    """

# ==================== MITARBEITER-BEREICH ====================

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    wartungen = Wartung.query.all()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mitarbeiter Bereich</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; padding: 20px; }
            .header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
            .header h1 { display: flex; align-items: center; gap: 10px; }
            .btn-logout { background: #ef4444; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 600; }
            .btn-logout:hover { background: #dc2626; }
            .tab { display: inline-block; padding: 10px 20px; cursor: pointer; background: #e2e8f0; border-radius: 8px 8px 0 0; margin-right: 4px; font-weight: 600; }
            .tab.active { background: white; color: #2563eb; }
            .tab-content { display: none; background: white; padding: 20px; border-radius: 0 8px 8px 8px; border: 1px solid #e2e8f0; }
            .tab-content.active { display: block; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; }
            th { background: #f1f5f9; font-weight: 700; }
            .btn { padding: 5px 12px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; color: white; display: inline-block; font-size: 0.8rem; font-weight: 600; }
            .btn-edit { background: #2563eb; }
            .btn-del { background: #ef4444; }
            .btn-qr { background: #000; }
            .btn-add { background: #16a34a; }
            .btn-wartung { background: #f59e0b; }
            .form-box { background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0; }
            .form-box input, .form-box textarea, .form-box select { padding: 8px 12px; border: 2px solid #e2e8f0; border-radius: 6px; margin-right: 5px; margin-bottom: 8px; }
            .form-box textarea { width: 100%; min-height: 80px; }
            .badge { padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; display: inline-block; }
            .verfuegbar { background: #dcfce7; color: #166534; }
            .reserviert { background: #fef3c7; color: #92400e; }
            .wartung { background: #fee2e2; color: #991b1b; }
            .offen { background: #fee2e2; color: #991b1b; }
            .inbearbeitung { background: #fef3c7; color: #92400e; }
            .erledigt { background: #dcfce7; color: #166534; }
            @media (max-width: 640px) {
                .header { flex-direction: column; text-align: center; gap: 10px; }
                table { font-size: 0.8rem; }
                th, td { padding: 6px; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔧 Mitarbeiter Dashboard</h1>
            <a href="/logout" class="btn-logout">🚪 Logout</a>
        </div>
        <a href="/">← Zurück zur Kundenansicht</a>
        <br><br>

        <div class="tab active" onclick="showTab('fahrraeder')">🚲 Fahrräder</div>
        <div class="tab" onclick="showTab('kunden')">👤 Kunden ({{ kunden|length }})</div>
        <div class="tab" onclick="showTab('wartungen')">🔧 Wartungen ({{ wartungen|length }})</div>

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
                {% for rad in raeder %}
                <tr>
                    <td>{{ rad.interne_nummer }}</td>
                    <td>{{ rad.marke }}</td>
                    <td>{{ rad.modell }}</td>
                    <td><span class="badge {{ 'verfuegbar' if rad.status == 'Verfügbar' else 'reserviert' if rad.status == 'Reserviert' else 'wartung' }}">{{ rad.status }}</span></td>
                    <td>{{ rad.standort }}</td>
                    <td>
                        <a href="/qr/{{ rad.id }}" class="btn btn-qr" target="_blank">📱 QR</a>
                        <a href="/rad/{{ rad.id }}" class="btn btn-wartung">🔧 Historie</a>
                        <a href="/mitarbeiter/delete/{{ rad.id }}" class="btn btn-del" onclick="return confirm('Sicher löschen?')">🗑️ Löschen</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="tab-kunden" class="tab-content">
            <h3>👤 Kunden mit Einwilligung</h3>
            <table>
                <tr><th>Name</th><th>Email</th><th>Adresse</th><th>DSGVO</th><th>Haftung</th><th>Datum</th></tr>
                {% for k in kunden %}
                <tr>
                    <td>{{ k.name }}</td>
                    <td>{{ k.email }}</td>
                    <td>{{ k.adresse }}, {{ k.plz_ort }}</td>
                    <td>{% if k.einwilligung_dsgvo %}✅{% else %}❌{% endif %}</td>
                    <td>{% if k.haftungsausschluss_akzeptiert %}✅{% else %}❌{% endif %}</td>
                    <td>{{ k.einwilligung_datum.strftime('%d.%m.%Y %H:%M') if k.einwilligung_datum else '-' }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="tab-wartungen" class="tab-content">
            <h3>🔧 Alle Wartungen</h3>
            <table>
                <tr><th>Fahrrad</th><th>Mitarbeiter</th><th>Problem</th><th>Status</th><th>Datum</th><th>Aktionen</th></tr>
                {% for w in wartungen %}
                <tr>
                    <td>{{ w.fahrrad_id }}</td>
                    <td>{{ w.mitarbeiter }}</td>
                    <td>{{ w.problem[:50] }}{% if w.problem|length > 50 %}...{% endif %}</td>
                    <td><span class="badge {{ 'offen' if w.status == 'Offen' else 'inbearbeitung' if w.status == 'In Bearbeitung' else 'erledigt' }}">{{ w.status }}</span></td>
                    <td>{{ w.erstellt_am.strftime('%d.%m.%Y %H:%M') }}</td>
                    <td>
                        <a href="/wartung/{{ w.id }}/edit" class="btn btn-edit">Bearbeiten</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <script>
            function showTab(tab) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
                document.getElementById('tab-' + tab).classList.add('active');
                event.target.classList.add('active');
            }
        </script>
    </body>
    </html>
    """, raeder=raeder, kunden=kunden, wartungen=wartungen)

# ==================== MITARBEITER-FUNKTIONEN ====================

@app.route('/mitarbeiter/add', methods=['POST'])
@login_required
def add_rad():
    rad = Fahrrad(
        interne_nummer=request.form['interne_nummer'],
        marke=request.form['marke'],
        modell=request.form['modell'],
        rahmengroesse=request.form.get('rahmengroesse', ''),
        farbe=request.form.get('farbe', ''),
        standort=request.form.get('standort', ''),
        status='Verfügbar'
    )
    db.session.add(rad)
    db.session.commit()
    return redirect(url_for('mitarbeiter'))

@app.route('/mitarbeiter/delete/<int:id>')
@login_required
def delete_rad(id):
    rad = Fahrrad.query.get(id)
    if rad:
        db.session.delete(rad)
        db.session.commit()
    return redirect(url_for('mitarbeiter'))

# ==================== QR-CODE & HISTORIE ====================

@app.route('/qr/<int:id>')
def show_qr(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404
    data = f"{PUBLIC_URL}/rad/{rad.id}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"""
    <h2>📱 QR-Code für {rad.marke} {rad.modell}</h2>
    <img src="data:image/png;base64,{img_str}" alt="QR Code">
    <br><br>
    <a href="/mitarbeiter">⬅ Zurück zum Dashboard</a>
    """
