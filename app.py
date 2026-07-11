from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

# ========== WICHTIG: ALLE KONFIGURATIONEN ==========
app.config['SECRET_KEY'] = 'mein_geheimer_schluessel_12345'
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
            return "❌ Falscher Name oder Passwort! <a href='/login'>Zurück</a>"
    
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f0f0; }
        .box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 300px; }
        input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        .btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%; }
    </style>
    </head>
    <body>
    <div class="box">
        <h2>🔐 Login</h2>
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

@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Fahrradverleih</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .btn { background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #218838; }
    </style>
    </head>
    <body>
    <h1>🚲 Fahrradverleih</h1>
    <a href="/mitarbeiter">🔐 Mitarbeiter-Login</a>
    <hr>
    """
    for rad in raeder:
        html += f"""
        <div class="card">
            <h3>{rad.marke} {rad.modell}</h3>
            <p><strong>Nr:</strong> {rad.interne_nummer}</p>
            <p><strong>Status:</strong> {rad.status}</p>
            <p><strong>Standort:</strong> {rad.standort}</p>
        </div>
        """
    html += "</body></html>"
    return html

# ==================== MITARBEITER-BEREICH ====================

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Mitarbeiter</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .btn { background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0069d9; }
    </style>
    </head>
    <body>
    <h1>🔧 Mitarbeiter Dashboard</h1>
    <a href="/logout">🚪 Logout</a> | <a href="/">⬅ Zurück</a>
    <hr>
    """
    for rad in raeder:
        html += f"""
        <div class="card">
            <p><strong>{rad.interne_nummer}</strong> - {rad.marke} {rad.modell} - {rad.status}</p>
            <a href="/qr/{rad.id}" class="btn">📱 QR-Code</a>
        </div>
        """
    html += "</body></html>"
    return html

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
    html = f'<h2>QR-Code für {rad.marke} {rad.modell}</h2>'
    html += f'<img src="data:image/png;base64,{img_str}">'
    html += '<br><br><a href="/mitarbeiter">⬅ Zurück</a>'
    return html

@app.route('/rad/<int:id>')
def fahrradakte(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404
    html = f'<h1>📋 Fahrradakte</h1>'
    html += f'<p><strong>Nr:</strong> {rad.interne_nummer}</p>'
    html += f'<p><strong>Marke:</strong> {rad.marke}</p>'
    html += f'<p><strong>Modell:</strong> {rad.modell}</p>'
    html += f'<p><strong>Status:</strong> {rad.status}</p>'
    html += '<a href="/mitarbeiter">⬅ Zurück</a>'
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
