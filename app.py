from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

# ========== SUPABASE DATENBANK ==========
# DEINE SUPABASE-URL (mit Passwort!)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Top83313%21%21%3F%3F@db.geasssxjynysfzypafqf.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'geheimer_schluessel'

db = SQLAlchemy(app)

ADMIN_USERNAME = "chef"
ADMIN_PASSWORD = "geheim123"

# ========== ÖFFENTLICHE URL (später anpassen!) ==========
PUBLIC_URL = "https://fahrradverleih.onrender.com"

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
    einwilligung_erteilt = db.Column(db.Boolean, default=False)
    einwilligung_datum = db.Column(db.DateTime)
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

# ==================== KUNDENANSICHT ====================

HTML_KUNDEN = """
<!DOCTYPE html>
<html>
<head><title>Fahrradverleih</title>
<style>
    body { font-family: sans-serif; background: #f3f4f6; padding: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
    .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; display: inline-block; }
    .verfuegbar { background: #d1fae5; color: #065f46; }
    .reserviert { background: #fef3c7; color: #92400e; }
    .wartung { background: #fee2e2; color: #991b1b; }
    .btn { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: 600; margin-top: 10px; }
    .btn:hover { background: #1d4ed8; }
    input { width: 100%; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; margin-bottom: 8px; font-size: 0.9rem; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .full-width { grid-column: span 2; }
    h3 { margin-top: 0; margin-bottom: 5px; }
    p { margin: 5px 0; color: #4b5563; }
    .checkbox-group { display: flex; align-items: flex-start; gap: 10px; margin: 10px 0; font-size: 0.9rem; }
    .checkbox-group input { width: auto; margin-top: 3px; }
    .ds-link { color: #2563eb; cursor: pointer; text-decoration: underline; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; }
    .modal-content { background: white; padding: 30px; border-radius: 12px; max-width: 600px; max-height: 80vh; overflow-y: auto; }
    .modal-close { float: right; background: #ef4444; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
    .footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 20px; }
</style>
</head>
<body>
    <h1>🚴 Fahrradverleih</h1>
    
    <div id="dsModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="document.getElementById('dsModal').style.display='none'">✕</button>
            <h2>📄 Datenschutzerklärung</h2>
            <hr>
            <p><strong>Verantwortlicher:</strong> Fahrradverleih GmbH, Musterstraße 1, 12345 Berlin</p>
            <p><strong>Zweck:</strong> Ihre Daten werden zur Abwicklung der Fahrradvermietung erhoben.</p>
            <p><strong>Speicherdauer:</strong> 7 Tage nach Rückgabe, dann Löschung.</p>
            <p><strong>Weitergabe:</strong> Keine Weitergabe an Dritte.</p>
            <p><strong>Widerruf:</strong> Jederzeit möglich unter <a href="/widerruf" target="_blank">Widerruf</a></p>
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
                        <input type="email" name="email" placeholder="E-Mail *" required>
                        <input type="text" name="ausweis" placeholder="Ausweis-Nr. *" required>
                        <input type="text" name="adresse" placeholder="Straße & Hausnr. *" required class="full-width">
                        <input type="text" name="plz_ort" placeholder="PLZ & Ort *" required class="full-width">
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="einwilligung_{{ rad.id }}" name="einwilligung" required>
                        <label for="einwilligung_{{ rad.id }}">
                            Ich stimme der Speicherung meiner Daten zu. 
                            <span class="ds-link" onclick="document.getElementById('dsModal').style.display='flex'">Datenschutzerklärung</span> gelesen.
                        </label>
                    </div>
                    <button type="submit" class="btn">Jetzt reservieren</button>
                </form>
            {% else %}
                <p style="color: #6b7280; font-style: italic;">Nicht verfügbar</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        <a href="/widerruf" target="_blank">Einwilligung widerrufen</a> | 
        <span class="ds-link" onclick="document.getElementById('dsModal').style.display='flex'">Datenschutzerklärung</span> | 
        <a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter</a>
    </div>

    <script>
        function validateForm(form) {
            if (!form.einwilligung.checked) {
                alert('Bitte stimmen Sie der Datenschutzerklärung zu.');
                return false;
            }
            return true;
        }
        window.onclick = function(event) {
            if (event.target === document.getElementById('dsModal')) {
                document.getElementById('dsModal').style.display = 'none';
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

# ==================== RESERVIEREN ====================

@app.route('/reservieren/<int:id>', methods=['POST'])
def reservieren(id):
    rad = Fahrrad.query.get(id)
    if not rad or rad.status != 'Verfügbar':
        return redirect(url_for('kundenansicht'))
    
    if request.form.get('einwilligung') != 'on':
        return "Fehler: Sie müssen der Datenschutzerklärung zustimmen.", 400
    
    kunde = Kunde(
        name=request.form['kunde'],
        email=request.form['email'],
        adresse=request.form['adresse'],
        plz_ort=request.form['plz_ort'],
        ausweis=request.form['ausweis'],
        einwilligung_erteilt=True,
        einwilligung_datum=datetime.utcnow(),
        fahrrad_id=rad.id
    )
    db.session.add(kunde)
    db.session.flush()
    
    reservierung = Reservierung(fahrrad_id=rad.id, kunde_id=kunde.id)
    db.session.add(reservierung)
    
    rad.status = 'Reserviert'
    db.session.commit()
    
    return redirect(url_for('kundenansicht'))

# ==================== WIDERRUF ====================

@app.route('/widerruf', methods=['GET', 'POST'])
def widerruf():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            return "Bitte E-Mail angeben.", 400
        
        kunden = Kunde.query.filter_by(email=email, einwilligung_erteilt=True).all()
        if not kunden:
            return "Keine Einwilligung für diese E-Mail gefunden.", 404
        
        for kunde in kunden:
            kunde.einwilligung_erteilt = False
            kunde.widerrufen_am = datetime.utcnow()
            kunde.name = "[Anonymisiert]"
            kunde.adresse = "[Anonymisiert]"
            kunde.plz_ort = "[Anonymisiert]"
            kunde.ausweis = "[Anonymisiert]"
        db.session.commit()
        
        return """
        <h2>✅ Einwilligung widerrufen</h2>
        <p>Ihre Daten wurden anonymisiert.</p>
        <a href="/">⬅ Zurück</a>
        """
    
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Widerruf</title></head>
    <body style="font-family:sans-serif; padding:40px; text-align:center;">
        <h2>Einwilligung widerrufen</h2>
        <p>E-Mail eingeben:</p>
        <form method="POST">
            <input type="email" name="email" required>
            <button type="submit">Widerrufen</button>
        </form>
        <br><a href="/">⬅ Zurück</a>
    </body>
    </html>
    """

# ==================== MITARBEITER ====================

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f2f2f2; }
        .btn { padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; color: white; text-decoration: none; display: inline-block; font-size: 0.8rem; }
        .btn-edit { background: #2563eb; }
        .btn-del { background: #ef4444; }
        .btn-qr { background: #000; }
        .btn-logout { background: #6b7280; float: right; }
        .badge { padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }
        .verfuegbar { background: #d1fae5; color: #065f46; }
        .reserviert { background: #fef3c7; color: #92400e; }
        .wartung { background: #fee2e2; color: #991b1b; }
    </style>
    </head>
    <body>
        <h1>🔧 Mitarbeiter <a href="/logout" class="btn btn-logout">Logout</a></h1>
        <a href="/">← Kundenansicht</a>

        <h3>Neues Fahrrad</h3>
        <form action="/mitarbeiter/add" method="POST">
            Nr: <input type="text" name="interne_nummer" required>
            Marke: <input type="text" name="marke" required>
            Modell: <input type="text" name="modell" required>
            Größe: <input type="text" name="rahmengroesse">
            Farbe: <input type="text" name="farbe">
            Standort: <input type="text" name="standort">
            <button type="submit" style="background:#10b981;color:white;border:none;padding:5px 15px;border-radius:4px;">Hinzufügen</button>
        </form>

        <h3>Fahrräder</h3>
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
                    <a href="/qr/{{ rad.id }}" class="btn btn-qr" target="_blank">QR</a>
                    <a href="/mitarbeiter/edit/{{ rad.id }}" class="btn btn-edit">Edit</a>
                    <a href="/mitarbeiter/delete/{{ rad.id }}" class="btn btn-del" onclick="return confirm('Löschen?')">Del</a>
                </td>
            </tr>
            {% endfor %}
        </table>

        <h3>Kunden</h3>
        <table>
            <tr><th>Name</th><th>Email</th><th>Einwilligung</th><th>Datum</th></tr>
            {% for k in kunden %}
            <tr>
                <td>{{ k.name }}</td>
                <td>{{ k.email }}</td>
                <td>{% if k.einwilligung_erteilt %}✅{% else %}❌{% endif %}</td>
                <td>{{ k.einwilligung_datum.strftime('%d.%m.%Y %H:%M') if k.einwilligung_datum else '-' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, raeder=raeder, kunden=kunden)

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
    <h1>Bearbeite {rad.marke}</h1>
    <form method="POST">
        Nr: <input type="text" name="interne_nummer" value="{rad.interne_nummer}"><br>
        Marke: <input type="text" name="marke" value="{rad.marke}"><br>
        Modell: <input type="text" name="modell" value="{rad.modell}"><br>
        Größe: <input type="text" name="rahmengroesse" value="{rad.rahmengroesse}"><br>
        Farbe: <input type="text" name="farbe" value="{rad.farbe}"><br>
        Standort: <input type="text" name="standort" value="{rad.standort}"><br>
        Status: <select name="status">
            <option value="Verfügbar" {"selected" if rad.status=="Verfügbar" else ""}>Verfügbar</option>
            <option value="Reserviert" {"selected" if rad.status=="Reserviert" else ""}>Reserviert</option>
            <option value="Wartung" {"selected" if rad.status=="Wartung" else ""}>Wartung</option>
        </select><br>
        <button type="submit">Speichern</button>
    </form>
    <a href="/mitarbeiter">Zurück</a>
    """

# ==================== QR-CODE ====================

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
    <h2>QR-Code für {rad.marke} {rad.modell}</h2>
    <img src="data:image/png;base64,{img_str}">
    <br><a href="/mitarbeiter">⬅ Zurück</a>
    """

@app.route('/rad/<int:id>')
def fahrradakte(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404
    return f"""
    <h1>Fahrradakte</h1>
    <p><strong>Nr:</strong> {rad.interne_nummer}</p>
    <p><strong>Marke:</strong> {rad.marke}</p>
    <p><strong>Modell:</strong> {rad.modell}</p>
    <p><strong>Status:</strong> {rad.status}</p>
    <a href="/">⬅ Zurück</a>
    """

# ==================== START (ANGEPASST FÜR RENDER) ====================

if __name__ == '__main__':
    # Render setzt die PORT-Umgebungsvariable automatisch
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
