from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

# ========== WICHTIG: SECRET_KEY für Session ==========
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
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('mitarbeiter'))
        else:
            return "<h2 style='color:red;'>❌ Falscher Name oder Passwort!</h2><a href='/login'>Zurück</a>"
    
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f3f4f6; }
        .box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 300px; }
        input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; }
        .btn { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; width: 100%; }
        .btn:hover { background: #1d4ed8; }
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

# ==================== KUNDENANSICHT ====================

HTML_KUNDEN = """
<!DOCTYPE html>
<html>
<head>
    <title>🚲 Fahrradverleih</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #f3f4f6; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; display: inline-block; }
        .verfuegbar { background: #d1fae5; color: #065f46; }
        .reserviert { background: #fef3c7; color: #92400e; }
        .wartung { background: #fee2e2; color: #991b1b; }
        .btn { background: #2563eb; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: 600; }
        .btn:hover { background: #1d4ed8; }
        input { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; margin-bottom: 8px; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .full-width { grid-column: span 2; }
        .checkbox-group { display: flex; gap: 10px; margin: 10px 0; font-size: 0.85rem; }
        .checkbox-group input { width: auto; }
        .footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 20px; }
        .footer a { color: #2563eb; text-decoration: none; }
        .warning-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 10px; margin: 10px 0; font-size: 0.85rem; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; }
        .modal-content { background: white; padding: 30px; border-radius: 12px; max-width: 600px; max-height: 80vh; overflow-y: auto; }
        .modal-close { float: right; background: #ef4444; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
        .ds-link { color: #2563eb; cursor: pointer; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚲 Fahrradverleih</h1>
        <p>Dein zuverlässiger Partner für Fahrradmiete</p>
    </div>
    
    <!-- DSGVO MODAL -->
    <div id="dsgvoModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('dsgvoModal').style.display='none'">✕</button>
            <h2>📄 Datenschutzerklärung (DSGVO)</h2>
            <hr>
            <p><strong>Verantwortlicher:</strong> Fahrradverleih GmbH, Musterstraße 1, 12345 Berlin</p>
            <p><strong>Zweck:</strong> Ihre Daten werden zur Abwicklung der Fahrradvermietung erhoben.</p>
            <p><strong>Speicherdauer:</strong> 7 Tage nach Rückgabe, dann Löschung.</p>
            <p><strong>Weitergabe:</strong> Keine Weitergabe an Dritte.</p>
            <p><strong>Widerruf:</strong> Jederzeit <a href="/widerruf" target="_blank">hier</a> möglich.</p>
        </div>
    </div>

    <!-- HAFTUNG MODAL -->
    <div id="haftungModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('haftungModal').style.display='none'">✕</button>
            <h2>⚠️ Haftungsausschluss</h2>
            <hr>
            <p><strong>1. Nutzung auf eigene Gefahr</strong><br>Die Nutzung der Fahrräder erfolgt ausschließlich auf eigene Gefahr.</p>
            <p><strong>2. Haftungsfreistellung</strong><br>Der Mieter haftet für alle Schäden durch unsachgemäße Nutzung.</p>
            <p><strong>3. Eigenverantwortung</strong><br>Der Mieter ist selbst verantwortlich für die Prüfung des Fahrrads auf Verkehrssicherheit.</p>
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
                            Ich habe die <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">Datenschutzerklärung</span> gelesen und stimme zu.
                        </label>
                    </div>

                    <div class="checkbox-group">
                        <input type="checkbox" id="haftung_{{ rad.id }}" name="haftung" required>
                        <label for="haftung_{{ rad.id }}">
                            Ich habe den <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">Haftungsausschluss</span> gelesen und akzeptiere ihn.
                        </label>
                    </div>

                    <div class="warning-box">
                        ⚠️ <strong>Wichtig:</strong> Nutzung auf eigene Gefahr.
                    </div>
                    
                    <button type="submit" class="btn">✅ Jetzt reservieren</button>
                </form>
            {% else %}
                <p style="color: #6b7280; font-style: italic;">🔒 Nicht verfügbar</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        <a href="/widerruf" target="_blank">🔒 Einwilligung widerrufen</a> | 
        <span class="ds-link" onclick="document.getElementById('dsgvoModal').style.display='flex'">📄 Datenschutz</span> | 
        <span class="ds-link" onclick="document.getElementById('haftungModal').style.display='flex'">⚠️ Haftung</span> | 
        <a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter</a>
    </div>

    <script>
        function validateForm(form) {
            if (!form.dsgvo.checked) {
                alert('Bitte stimmen Sie der Datenschutzerklärung zu.');
                return false;
            }
            if (!form.haftung.checked) {
                alert('Bitte akzeptieren Sie den Haftungsausschluss.');
                return false;
            }
            return true;
        }
        window.onclick = function(event) {
            if (event.target.className === 'modal') {
                event.target.style.display = 'none';
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
    
    reservierung = Reservierung(fahrrad_id=rad.id, kunde_id=kunde.id)
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

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    return render_template_string("""
    <h1>🔧 Mitarbeiter Dashboard</h1>
    <a href="/logout">Logout</a> | <a href="/">Zurück</a>
    <hr>
    <h3>Neues Fahrrad</h3>
    <form action="/mitarbeiter/add" method="POST">
        Nr: <input type="text" name="interne_nummer" required>
        Marke: <input type="text" name="marke" required>
        Modell: <input type="text" name="modell" required>
        <button type="submit">Hinzufügen</button>
    </form>
    <h3>Alle Fahrräder</h3>
    <table border="1">
        <tr><th>Nr</th><th>Marke</th><th>Modell</th><th>Status</th><th>Aktionen</th></tr>
        {% for rad in raeder %}
        <tr>
            <td>{{ rad.interne_nummer }}</td>
            <td>{{ rad.marke }}</td>
            <td>{{ rad.modell }}</td>
            <td>{{ rad.status }}</td>
            <td>
                <a href="/qr/{{ rad.id }}">QR</a>
                <a href="/mitarbeiter/delete/{{ rad.id }}" onclick="return confirm('Löschen?')">Löschen</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    <h3>Kunden</h3>
    <table border="1">
        <tr><th>Name</th><th>Email</th><th>DSGVO</th></tr>
        {% for k in kunden %}
        <tr>
            <td>{{ k.name }}</td>
            <td>{{ k.email }}</td>
            <td>{% if k.einwilligung_dsgvo %}✅{% else %}❌{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
    """, raeder=raeder, kunden=kunden)

@app.route('/mitarbeiter/add', methods=['POST'])
@login_required
def add_rad():
    rad = Fahrrad(
        interne_nummer=request.form['interne_nummer'],
        marke=request.form['marke'],
        modell=request.form['modell'],
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
    return f'<h2>QR-Code für {rad.marke} {rad.modell}</h2><img src="data:image/png;base64,{img_str}"><br><a href="/mitarbeiter">Zurück</a>'

@app.route('/rad/<int:id>')
def fahrradakte(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404
    return f'<h1>Fahrradakte</h1><p>{rad.marke} {rad.modell}</p><a href="/">Zurück</a>'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
