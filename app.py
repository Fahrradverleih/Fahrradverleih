from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

# ========== SUPABASE DATENBANK (über Environment Variable) ==========
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'geheimer_schluessel'

db = SQLAlchemy(app)

ADMIN_USERNAME = "chef"
ADMIN_PASSWORD = "geheim123"

# ========== ÖFFENTLICHE URL (für QR-Codes) ==========
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

# ==================== LOGIN ====================

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
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f3f4f6; }
        .box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 300px; }
        input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; }
        .btn { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; width: 100%; }
    </style>
    </head>
    <body>
    <div class="box">
        <h2>🔐 Mitarbeiter Login</h2>
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

# ==================== KUNDENANSICHT (MIT DSGVO & HAFTUNG) ====================

HTML_KUNDEN = """
<!DOCTYPE html>
<html>
<head><title>Fahrradverleih</title>
<style>
    body { font-family: sans-serif; background: #f3f4f6; padding: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }
    .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; display: inline-block; }
    .verfuegbar { background: #d1fae5; color: #065f46; }
    .reserviert { background: #fef3c7; color: #92400e; }
    .wartung { background: #fee2e2; color: #991b1b; }
    .btn { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: 600; margin-top: 10px; }
    .btn:hover { background: #1d4ed8; }
    .btn:disabled { background: #9ca3af; cursor: not-allowed; }
    input { width: 100%; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; margin-bottom: 8px; font-size: 0.9rem; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .full-width { grid-column: span 2; }
    h3 { margin-top: 0; margin-bottom: 5px; }
    p { margin: 5px 0; color: #4b5563; }
    .checkbox-group { display: flex; align-items: flex-start; gap: 10px; margin: 10px 0; font-size: 0.85rem; }
    .checkbox-group input { width: auto; margin-top: 3px; }
    .checkbox-group label { color: #374151; }
    .ds-link { color: #2563eb; cursor: pointer; text-decoration: underline; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; }
    .modal-content { background: white; padding: 30px; border-radius: 12px; max-width: 600px; max-height: 80vh; overflow-y: auto; }
    .modal-close { float: right; background: #ef4444; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
    .footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 20px; }
    .warning-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 10px; margin: 10px 0; font-size: 0.85rem; }
</style>
</head>
<body>
    <h1>🚴 Fahrradverleih</h1>
    
    <!-- ====== DSGVO MODAL ====== -->
    <div id="dsgvoModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('dsgvoModal').style.display='none'">✕</button>
            <h2>📄 Datenschutzerklärung (DSGVO)</h2>
            <hr>
            <p><strong>Verantwortlicher:</strong> Fahrradverleih GmbH, Musterstraße 1, 12345 Berlin</p>
            <p><strong>Zweck der Datenerhebung:</strong> Ihre Daten (Name, Adresse, E-Mail, Ausweisnummer) werden ausschließlich zur Abwicklung der Fahrradvermietung erhoben und gespeichert. Ohne diese Daten können wir keinen Mietvertrag abschließen.</p>
            <p><strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) und Art. 6 Abs. 1 lit. a DSGVO (Einwilligung).</p>
            <p><strong>Speicherdauer:</strong> Ihre Daten werden bis zu 7 Tage nach der Rückgabe des Fahrrads gespeichert und dann gelöscht, sofern keine gesetzlichen Aufbewahrungspflichten (z.B. steuerrechtlich) bestehen.</p>
            <p><strong>Weitergabe:</strong> Ihre Daten werden nicht an Dritte weitergegeben.</p>
            <p><strong>Ihre Rechte:</strong> Sie haben jederzeit das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung und Datenübertragbarkeit. Kontaktieren Sie uns unter <a href="mailto:datenschutz@fahrradverleih.de">datenschutz@fahrradverleih.de</a>.</p>
            <p><strong>Widerruf:</strong> Sie können Ihre Einwilligung jederzeit <a href="/widerruf" target="_blank">hier</a> widerrufen.</p>
            <p><small>Stand: Juli 2026</small></p>
        </div>
    </div>

    <!-- ====== HAFTUNG MODAL ====== -->
    <div id="haftungModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('haftungModal').style.display='none'">✕</button>
            <h2>⚠️ Haftungsausschluss</h2>
            <hr>
            <p><strong>1. Nutzung auf eigene Gefahr</strong><br>
            Die Nutzung der Fahrräder erfolgt ausschließlich auf eigene Gefahr. Der Mieter versichert, dass er das Fahrrad sicher beherrscht und alle Verkehrsregeln kennt und einhält.</p>
            <p><strong>2. Haftungsfreistellung</strong><br>
            Der Mieter stellt den Verleiher von allen Ansprüchen Dritter frei, die im Zusammenhang mit der Nutzung des Fahrrads entstehen. Der Mieter haftet für alle Schäden, die durch unsachgemäße Nutzung, Missachtung der Verkehrsregeln oder höhere Gewalt entstehen.</p>
            <p><strong>3. Eigenverantwortung</strong><br>
            Der Mieter ist selbst verantwortlich für die Prüfung des Fahrrads auf Verkehrssicherheit (Bremsen, Beleuchtung, Reifen) vor Fahrtantritt. Bei Mängeln ist der Verleiher unverzüglich zu informieren.</p>
            <p><strong>4. Versicherung</strong><br>
            Der Mieter ist angehalten, eine eigene Haftpflichtversicherung abzuschließen, die Schäden im Zusammenhang mit der Fahrradnutzung abdeckt.</p>
            <p><strong>5. Unfälle</strong><br>
            Bei Unfällen oder Stürzen haftet der Mieter selbst. Der Verleiher übernimmt keine Haftung für Personen- oder Sachschäden, die während der Mietzeit entstehen.</p>
            <p><small>Stand: Juli 2026</small></p>
        </div>
    </div>

    <div class="grid">
        {% for rad in raeder %}
        <div class="card">
            <h3>{{ rad.marke }} {{ rad.modell }}</h3>
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
                        <input type="email" name="email" placeholder="E-Mail-Adresse *" required>
                        <input type="text" name="ausweis" placeholder="Ausweis-Nr. *" required>
                        <input type="text" name="adresse" placeholder="Straße & Hausnr. *" required class="full-width">
                        <input type="text" name="plz_ort" placeholder="PLZ & Ort *" required class="full-width">
                    </div>
                    
                    <!-- ====== DSGVO CHECKBOX ====== -->
                    <div class="checkbox-group">
                        <input type="checkbox" id="dsgvo_{{ rad.id }}" name="dsgvo" required>
                        <label for="dsgvo_{{ rad.id }}">
                            Ich habe die <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">Datenschutzerklärung</span> gelesen und stimme der Speicherung meiner Daten gemäß DSGVO zu. 
                            Die Einwilligung kann jederzeit <a href="/widerruf" target="_blank">widerrufen</a> werden.
                        </label>
                    </div>

                    <!-- ====== HAFTUNG CHECKBOX ====== -->
                    <div class="checkbox-group">
                        <input type="checkbox" id="haftung_{{ rad.id }}" name="haftung" required>
                        <label for="haftung_{{ rad.id }}">
                            Ich habe den <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">Haftungsausschluss</span> gelesen und akzeptiere, dass ich die volle Verantwortung für die Nutzung des Fahrrads trage.
                        </label>
                    </div>

                    <div class="warning-box">
                        ⚠️ <strong>Wichtig:</strong> Mit der Buchung bestätigen Sie, dass Sie das Fahrrad auf Verkehrssicherheit geprüft haben und die Nutzung auf eigene Gefahr erfolgt.
                    </div>
                    
                    <button type="submit" class="btn">Jetzt verbindlich reservieren</button>
                </form>
            {% else %}
                <p style="color: #6b7280; font-style: italic;">Aktuell nicht verfügbar</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        <a href="/widerruf" target="_blank">Einwilligung widerrufen</a> | 
        <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">Datenschutzerklärung</span> | 
        <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">Haftungsausschluss</span> | 
        <a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter-Login</a>
    </div>

    <script>
        function validateForm(form) {
            // Prüfe DSGVO-Checkbox
            const dsgvo = form.querySelector('input[name="dsgvo"]');
            if (!dsgvo.checked) {
                alert('Bitte stimmen Sie der Datenschutzerklärung zu.');
                return false;
            }
            // Prüfe Haftungs-Checkbox
            const haftung = form.querySelector('input[name="haftung"]');
            if (!haftung.checked) {
                alert('Bitte akzeptieren Sie den Haftungsausschluss.');
                return false;
            }
            return true;
        }
        // Modal schließen bei Klick außerhalb
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

# ==================== RESERVIEREN (MIT DSGVO + HAFTUNG) ====================

@app.route('/reservieren/<int:id>', methods=['POST'])
def reservieren(id):
    rad = Fahrrad.query.get(id)
    if not rad or rad.status != 'Verfügbar':
        return redirect(url_for('kundenansicht'))
    
    # Prüfe DSGVO und Haftung
    dsgvo_ok = request.form.get('dsgvo') == 'on'
    haftung_ok = request.form.get('haftung') == 'on'
    
    if not dsgvo_ok:
        return "Fehler: Sie müssen der Datenschutzerklärung zustimmen.", 400
    if not haftung_ok:
        return "Fehler: Sie müssen den Haftungsausschluss akzeptieren.", 400
    
    # Kunden anlegen
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
    
    # Reservierung speichern
    reservierung = Reservierung(
        fahrrad_id=rad.id,
        kunde_id=kunde.id
    )
    db.session.add(reservierung)
    
    # Fahrrad auf reserviert setzen
    rad.status = 'Reserviert'
    db.session.commit()
    
    flash('Vielen Dank! Ihre Reservierung wurde erfolgreich gebucht. Bitte prüfen Sie vor Fahrtantritt die Verkehrssicherheit des Fahrrads.', 'success')
    return redirect(url_for('kundenansicht'))

# ==================== WIDERRUF DER EINWILLIGUNG ====================

@app.route('/widerruf', methods=['GET', 'POST'])
def widerruf():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            return "Bitte E-Mail-Adresse angeben.", 400
        
        # Kunden mit dieser Email finden
        kunden = Kunde.query.filter_by(email=email, einwilligung_dsgvo=True).all()
        if not kunden:
            return "Keine Einwilligung für diese E-Mail-Adresse gefunden.", 404
        
        # Alle Einwilligungen widerrufen (Daten anonymisieren)
        for kunde in kunden:
            kunde.einwilligung_dsgvo = False
            kunde.widerrufen_am = datetime.utcnow()
            # Daten anonymisieren (außer für gesetzliche Pflichten)
            kunde.name = "[Anonymisiert]"
            kunde.adresse = "[Anonymisiert]"
            kunde.plz_ort = "[Anonymisiert]"
            kunde.ausweis = "[Anonymisiert]"
            # Email bleibt für Nachweis
        db.session.commit()
        
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Widerruf erfolgreich</title></head>
        <body style="font-family:sans-serif; padding:40px; text-align:center;">
            <h2>✅ Einwilligung erfolgreich widerrufen</h2>
            <p>Ihre Daten wurden anonymisiert. Die E-Mail-Adresse bleibt für Nachweiszwecke gespeichert.</p>
            <a href="/">⬅ Zurück zur Startseite</a>
        </body>
        </html>
        """
    
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Einwilligung widerrufen</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f3f4f6; }
        .box { background: white; padding: 40px; border-radius: 12px; max-width: 500px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
        input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; }
        .btn { background: #ef4444; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; width: 100%; }
        .btn:hover { background: #dc2626; }
    </style>
    </head>
    <body>
        <div class="box">
            <h2>🔒 Einwilligung widerrufen</h2>
            <p>Geben Sie Ihre E-Mail-Adresse ein, mit der Sie reserviert haben.</p>
            <p style="font-size:0.9rem; color:#6b7280;">Ihre Daten werden dann anonymisiert.</p>
            <form method="POST">
                <input type="email" name="email" placeholder="E-Mail-Adresse *" required>
                <button type="submit" class="btn">Einwilligung widerrufen</button>
            </form>
            <br>
            <a href="/">⬅ Zurück zur Startseite</a>
        </div>
    </body>
    </html>
    """

# ==================== MITARBEITER-BEREICH ====================

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter Bereich</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f9fafb; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .btn { padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; color: white; display: inline-block; margin-right: 2px; font-size: 0.8rem; }
        .btn-edit { background: #2563eb; }
        .btn-del { background: #ef4444; }
        .btn-qr { background: #000; color: white; }
        .form-box { background: #f9fafb; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e5e7eb; }
        .btn-logout { background: #6b7280; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; float: right; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; display: inline-block; }
        .verfuegbar { background: #d1fae5; color: #065f46; }
        .reserviert { background: #fef3c7; color: #92400e; }
        .wartung { background: #fee2e2; color: #991b1b; }
        .tab { display: inline-block; padding: 10px 20px; cursor: pointer; background: #e5e7eb; border-radius: 8px 8px 0 0; margin-right: 4px; }
        .tab.active { background: white; font-weight: bold; }
        .tab-content { display: none; background: white; padding: 20px; border-radius: 0 8px 8px 8px; border: 1px solid #e5e7eb; }
        .tab-content.active { display: block; }
    </style>
    </head>
    <body>
        <h1>🔧 Mitarbeiter Dashboard <a href="/logout" class="btn-logout">Logout</a></h1>
        <a href="/">← Zurück zur Kundenansicht</a>
        <br><br>

        <div class="tab active" onclick="showTab('fahrraeder')">🚲 Fahrräder</div>
        <div class="tab" onclick="showTab('kunden')">👤 Kunden ({{ kunden|length }})</div>

        <div id="tab-fahrraeder" class="tab-content active">
            <div class="form-box">
                <h3>Neues Fahrrad anlegen</h3>
                <form action="/mitarbeiter/add" method="POST">
                    Nr: <input type="text" name="interne_nummer" required style="width:80px;">
                    Marke: <input type="text" name="marke" required style="width:120px;">
                    Modell: <input type="text" name="modell" required style="width:120px;">
                    Größe: <input type="text" name="rahmengroesse" style="width:60px;">
                    Farbe: <input type="text" name="farbe" style="width:80px;">
                    Standort: <input type="text" name="standort" style="width:100px;">
                    <button type="submit" class="btn" style="background:#10b981;">Hinzufügen</button>
                </form>
            </div>

            <h3>Alle Fahrräder verwalten</h3>
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
                        <a href="/mitarbeiter/edit/{{ rad.id }}" class="btn btn-edit">Bearbeiten</a>
                        <a href="/mitarbeiter/delete/{{ rad.id }}" class="btn btn-del" onclick="return confirm('Sicher löschen?')">Löschen</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="tab-kunden" class="tab-content">
            <h3>Kunden mit Einwilligung</h3>
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
    """, raeder=raeder, kunden=kunden)

# ==================== MITARBEITER-FUNKTIONEN ====================

@app.route('/mitarbeiter/add', methods=['POST'])
@login_required
def add_rad():
    neues_rad = Fahrrad(
        interne_nummer=request.form['interne_nummer'],
        marke=request.form['marke'],
        modell=request.form['modell'],
        rahmengroesse=request.form.get('rahmengroesse', ''),
        farbe=request.form.get('farbe', ''),
        standort=request.form.get('standort', ''),
        status='Verfügbar'
    )
    db.session.add(neues_rad)
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

@app.route('/mitarbeiter/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_rad(id):
    rad = Fahrrad.query.get(id)
    if request.method == 'POST':
        rad.interne_nummer = request.form['interne_nummer']
        rad.marke = request.form['marke']
        rad.modell = request.form['modell']
        rad.rahmengroesse = request.form.get('rahmengroesse', '')
        rad.farbe = request.form.get('farbe', '')
        rad.standort = request.form.get('standort', '')
        rad.status = request.form['status']
        db.session.commit()
        return redirect(url_for('mitarbeiter'))

    return f"""
    <h1>Bearbeite {rad.marke} {rad.modell}</h1>
    <form method="POST">
        Nr: <input type="text" name="interne_nummer" value="{rad.interne_nummer}"><br>
        Marke: <input type="text" name="marke" value="{rad.marke}"><br>
        Modell: <input type="text" name="modell" value="{rad.modell}"><br>
        Größe: <input type="text" name="rahmengroesse" value="{rad.rahmengroesse}"><br>
        Farbe: <input type="text" name="farbe" value="{rad.farbe}"><br>
        Standort: <input type="text" name="standort" value="{rad.standort}"><br>
        Status:
        <select name="status">
            <option value="Verfügbar" {"selected" if rad.status == "Verfügbar" else ""}>Verfügbar</option>
            <option value="Reserviert" {"selected" if rad.status == "Reserviert" else ""}>Reserviert</option>
            <option value="Wartung" {"selected" if rad.status == "Wartung" else ""}>Wartung</option>
        </select><br><br>
        <button type="submit">Speichern</button>
    </form>
    <br><a href="/mitarbeiter">Zurück zum Dashboard</a>
    """

# ==================== QR-CODE ====================

@app.route('/qr/<int:id>')
def show_qr(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Fahrrad nicht gefunden", 404
    data = f"{PUBLIC_URL}/rad/{rad.id}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>QR-Code für {rad.marke} {rad.modell}</title>
    <style>
        body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #f3f4f6; }}
        .box {{ background: white; padding: 40
