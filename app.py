from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = 'geheimer_schluessel'
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

@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()
    html = '<!DOCTYPE html>'
    html += '<html><head><title>Fahrradverleih</title>'
    html += '<style>'
    html += 'body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }'
    html += '.header { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; padding: 30px 20px; border-radius: 16px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }'
    html += '.header h1 { font-size: 2rem; display: flex; align-items: center; gap: 10px; }'
    html += '.header .sub { font-size: 0.9rem; opacity: 0.9; }'
    html += '.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 24px; }'
    html += '.card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }'
    html += '.card h3 { font-size: 1.3rem; color: #1e293b; margin-bottom: 8px; }'
    html += '.badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; text-transform: uppercase; }'
    html += '.verfuegbar { background: #dcfce7; color: #166534; }'
    html += '.reserviert { background: #fef3c7; color: #92400e; }'
    html += '.wartung { background: #fee2e2; color: #991b1b; }'
    html += '.btn { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: 700; font-size: 1rem; }'
    html += '.btn:hover { transform: scale(1.02); }'
    html += 'input { width: 100%; padding: 10px 12px; border: 2px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px; }'
    html += '.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }'
    html += '.full-width { grid-column: span 2; }'
    html += '.checkbox-group { display: flex; align-items: flex-start; gap: 10px; margin: 10px 0; font-size: 0.85rem; }'
    html += '.checkbox-group input { width: 18px; height: 18px; margin-top: 2px; }'
    html += '.footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #6b7280; border-top: 1px solid #e2e8f0; padding-top: 20px; display: flex; justify-content: center; gap: 20px; }'
    html += '.footer a { color: #2563eb; text-decoration: none; font-weight: 600; }'
    html += '.warning-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 10px 0; font-size: 0.85rem; }'
    html += '</style>'
    html += '</head><body>'
    html += '<div class="header"><div><h1>🚲 Fahrradverleih</h1><div class="sub">Dein zuverlässiger Partner für Fahrradmiete</div></div><div class="logo-img">⭐ 4.8</div></div>'
    html += '<div class="grid">'
    for rad in raeder:
        html += '<div class="card">'
        html += f'<h3>🚲 {rad.marke} {rad.modell}</h3>'
        html += f'<p><strong>Nr:</strong> {rad.interne_nummer}<br><strong>Größe:</strong> {rad.rahmengroesse} / {rad.farbe}<br><strong>Standort:</strong> {rad.standort}</p>'
        status_class = rad.status.lower() if rad.status else 'verfuegbar'
        html += f'<span class="badge {status_class}">{rad.status}</span>'
        html += '<br><br>'
        if rad.status == 'Verfügbar':
            html += f'<form action="/reservieren/{rad.id}" method="POST" onsubmit="return validateForm(this)">'
            html += '<input type="text" name="kunde" placeholder="Vor- und Nachname *" required class="full-width">'
            html += '<div class="form-grid">'
            html += '<input type="email" name="email" placeholder="E-Mail *" required>'
            html += '<input type="text" name="ausweis" placeholder="Ausweis-Nr. *" required>'
            html += '<input type="text" name="adresse" placeholder="Straße & Hausnr. *" required class="full-width">'
            html += '<input type="text" name="plz_ort" placeholder="PLZ & Ort *" required class="full-width">'
            html += '</div>'
            html += '<div class="checkbox-group">'
            html += f'<input type="checkbox" id="dsgvo_{rad.id}" name="dsgvo" required>'
            html += f'<label for="dsgvo_{rad.id}">Ich habe die Datenschutzerklärung gelesen und stimme zu.</label>'
            html += '</div>'
            html += '<div class="checkbox-group">'
            html += f'<input type="checkbox" id="haftung_{rad.id}" name="haftung" required>'
            html += f'<label for="haftung_{rad.id}">Ich habe den Haftungsausschluss gelesen und akzeptiere ihn.</label>'
            html += '</div>'
            html += '<div class="warning-box">⚠️ <strong>Wichtig:</strong> Nutzung auf eigene Gefahr.</div>'
            html += '<button type="submit" class="btn">✅ Jetzt reservieren</button>'
            html += '</form>'
        else:
            html += '<p style="color: #6b7280; font-style: italic;">🔒 Nicht verfügbar</p>'
        html += '</div>'
    html += '</div>'
    html += '<div class="footer">'
    html += '<a href="/widerruf">Einwilligung widerrufen</a>'
    html += '<a href="/mitarbeiter">Mitarbeiter-Login</a>'
    html += '</div>'
    html += '<script>'
    html += 'function validateForm(form) {'
    html += 'if (!form.dsgvo.checked) { alert("Bitte stimmen Sie der Datenschutzerklärung zu."); return false; }'
    html += 'if (!form.haftung.checked) { alert("Bitte akzeptieren Sie den Haftungsausschluss."); return false; }'
    html += 'return true; }'
    html += '</script>'
    html += '</body></html>'
    return html

# ==================== RESERVIEREN ====================

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

# ==================== WIDERRUF ====================

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

# ==================== MITARBEITER ====================

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    html = '<!DOCTYPE html><html><head><title>Mitarbeiter</title>'
    html += '<style>'
    html += 'body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }'
    html += '.header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }'
    html += '.btn-logout { background: #ef4444; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; }'
    html += '.card { background: white; padding: 20px; margin: 10px 0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }'
    html += '.btn { background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }'
    html += '</style></head><body>'
    html += '<div class="header"><h1>🔧 Mitarbeiter Dashboard</h1><a href="/logout" class="btn-logout">Logout</a></div>'
    html += '<a href="/">← Zurück</a><hr>'
    for rad in raeder:
        html += f'<div class="card"><p><strong>{rad.interne_nummer}</strong> - {rad.marke} {rad.modell} - {rad.status}</p>'
        html += f'<a href="/qr/{rad.id}" class="btn">QR-Code</a>'
        html += f'<a href="/rad/{rad.id}" class="btn">Historie</a>'
        html += '</div>'
    html += '</body></html>'
    return html

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
    html = '<h2>QR-Code für ' + rad.marke + ' ' + rad.modell + '</h2>'
    html += '<img src="data:image/png;base64,' + img_str + '">'
    html += '<br><br><a href="/mitarbeiter">⬅ Zurück</a>'
    return html

@app.route('/rad/<int:id>')
def fahrradakte(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404
    html = '<h1>📋 Fahrradakte</h1>'
    html += '<p><strong>Nr:</strong> ' + rad.interne_nummer + '</p>'
    html += '<p><strong>Marke:</strong> ' + rad.marke + '</p>'
    html += '<p><strong>Modell:</strong> ' + rad.modell + '</p>'
    html += '<p><strong>Status:</strong> ' + rad.status + '</p>'
    html += '<a href="/mitarbeiter">⬅ Zurück</a>'
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
