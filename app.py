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
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
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

@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()
    html = '<!DOCTYPE html><html><head><title>🚲 Fahrradverleih</title>'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    html += '<style>'
    html += 'body { font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; padding: 20px; }'
    html += '.header { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; padding: 30px 20px; border-radius: 16px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }'
    html += '.header h1 { font-size: 2rem; display: flex; align-items: center; gap: 10px; }'
    html += '.header .sub { font-size: 0.9rem; opacity: 0.9; }'
    html += '.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 24px; }'
    html += '.card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); transition: transform 0.2s; }'
    html += '.card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }'
    html += '.card h3 { font-size: 1.3rem; color: #1e293b; margin-bottom: 8px; }'
    html += '.card p { color: #64748b; margin: 4px 0; }'
    html += '.badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; text-transform: uppercase; }'
    html += '.verfuegbar { background: #dcfce7; color: #166534; }'
    html += '.reserviert { background: #fef3c7; color: #92400e; }'
    html += '.wartung { background: #fee2e2; color: #991b1b; }'
    html += '.btn { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: 700; font-size: 1rem; transition: transform 0.2s; }'
    html += '.btn:hover { transform: scale(1.02); }'
    html += 'input { width: 100%; padding: 10px 12px; border: 2px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px; font-size: 0.95rem; }'
    html += 'input:focus { border-color: #2563eb; outline: none; }'
    html += '.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }'
    html += '.full-width { grid-column: span 2; }'
    html += '.checkbox-group { display: flex; align-items: flex-start; gap: 10px; margin: 10px 0; font-size: 0.85rem; color: #334155; }'
    html += '.checkbox-group input { width: 18px; height: 18px; margin-top: 2px; accent-color: #2563eb; }'
    html += '.checkbox-group label { line-height: 1.4; }'
    html += '.ds-link { color: #2563eb; cursor: pointer; text-decoration: underline; font-weight: 600; }'
    html += '.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; padding: 20px; }'
    html += '.modal-content { background: white; padding: 30px; border-radius: 16px; max-width: 600px; max-height: 80vh; overflow-y: auto; }'
    html += '.modal-close { float: right; background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }'
    html += '.footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 20px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }'
    html += '.footer a { color: #2563eb; text-decoration: none; font-weight: 600; }'
    html += '.footer a:hover { color: #7c3aed; text-decoration: underline; }'
    html += '.warning-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 10px 0; font-size: 0.85rem; color: #991b1b; border-radius: 4px; }'
    html += '@media (max-width: 640px) { .header { flex-direction: column; text-align: center; } .header h1 { font-size: 1.5rem; } .grid { grid-template-columns: 1fr; } .form-grid { grid-template-columns: 1fr; } .full-width { grid-column: span 1; } }'
    html += '.logo-img { font-size: 2.5rem; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 12px; }'
    html += '</style></head><body>'
    html += '<div class="header"><div><h1><span>🚲</span> Fahrradverleih</h1><div class="sub">📍 Dein zuverlässiger Partner für Fahrradmiete</div></div><div class="logo-img">⭐ 4.8</div></div>'
    
    html += '<div id="dsgvoModal" class="modal"><div class="modal-content"><button class="modal-close" onclick="document.getElementById(\'dsgvoModal\').style.display=\'none\'">✕</button>'
    html += '<h2>📄 Datenschutzerklärung (DSGVO)</h2><hr>'
    html += '<p><strong>Verantwortlicher:</strong> Fahrradverleih GmbH, Musterstraße 1, 12345 Berlin</p>'
    html += '<p><strong>Zweck:</strong> Ihre Daten werden zur Abwicklung der Fahrradvermietung erhoben.</p>'
    html += '<p><strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) und Art. 6 Abs. 1 lit. a DSGVO (Einwilligung).</p>'
    html += '<p><strong>Speicherdauer:</strong> 7 Tage nach Rückgabe, dann Löschung.</p>'
    html += '<p><strong>Weitergabe:</strong> Keine Weitergabe an Dritte.</p>'
    html += '<p><strong>Ihre Rechte:</strong> Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung und Datenübertragbarkeit. Kontakt: <a href="mailto:datenschutz@fahrradverleih.de">datenschutz@fahrradverleih.de</a></p>'
    html += '<p><strong>Widerruf:</strong> Jederzeit <a href="/widerruf" target="_blank">hier</a> möglich.</p>'
    html += '<p><small>Stand: Juli 2026</small></p></div></div>'
    
    html += '<div id="haftungModal" class="modal"><div class="modal-content"><button class="modal-close" onclick="document.getElementById(\'haftungModal\').style.display=\'none\'">✕</button>'
    html += '<h2>⚠️ Haftungsausschluss</h2><hr>'
    html += '<p><strong>1. Nutzung auf eigene Gefahr</strong><br>Die Nutzung der Fahrräder erfolgt ausschließlich auf eigene Gefahr. Der Mieter versichert, dass er das Fahrrad sicher beherrscht und alle Verkehrsregeln kennt.</p>'
    html += '<p><strong>2. Haftungsfreistellung</strong><br>Der Mieter stellt den Verleiher von allen Ansprüchen Dritter frei, die im Zusammenhang mit der Nutzung entstehen. Der Mieter haftet für alle Schäden durch unsachgemäße Nutzung.</p>'
    html += '<p><strong>3. Eigenverantwortung</strong><br>Der Mieter ist selbst verantwortlich für die Prüfung des Fahrrads auf Verkehrssicherheit (Bremsen, Beleuchtung, Reifen) vor Fahrtantritt.</p>'
    html += '<p><strong>4. Versicherung</strong><br>Der Mieter ist angehalten, eine eigene Haftpflichtversicherung abzuschließen.</p>'
    html += '<p><strong>5. Unfälle</strong><br>Bei Unfällen oder Stürzen haftet der Mieter selbst. Der Verleiher übernimmt keine Haftung für Personen- oder Sachschäden.</p>'
    html += '<p><small>Stand: Juli 2026</small></p></div></div>'
    
    html += '<div class="grid">'
    for rad in raeder:
        html += '<div class="card">'
        html += f'<h3>🚲 {rad.marke} {rad.modell}</h3>'
        html += f'<p><strong>Nr:</strong> {rad.interne_nummer}<br><strong>Größe:</strong> {rad.rahmengroesse} / {rad.farbe}<br><strong>Standort:</strong> {rad.standort}</p>'
        status_class = rad.status.lower() if rad.status else 'verfuegbar'
        html += f'<span class="badge {status_class}">{rad.status}</span><br><br>'
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
            html += f'<label for="dsgvo_{rad.id}">Ich habe die <span class="ds-link" onclick="document.getElementById(\'dsgvoModal\').style.display=\'flex\'">Datenschutzerklärung</span> gelesen und stimme der Speicherung meiner Daten gemäß DSGVO zu. Die Einwilligung kann jederzeit <a href="/widerruf" target="_blank">widerrufen</a> werden.</label>'
            html += '</div>'
            html += '<div class="checkbox-group">'
            html += f'<input type="checkbox" id="haftung_{rad.id}" name="haftung" required>'
            html += f'<label for="haftung_{rad.id}">Ich habe den <span class="ds-link" onclick="document.getElementById(\'haftungModal\').style.display=\'flex\'">Haftungsausschluss</span> gelesen und akzeptiere, dass ich die volle Verantwortung für die Nutzung trage.</label>'
            html += '</div>'
            html += '<div class="warning-box">⚠️ <strong>Wichtig:</strong> Mit der Buchung bestätigen Sie die Prüfung auf Verkehrssicherheit und die Nutzung auf eigene Gefahr.</div>'
            html += '<button type="submit" class="btn">✅ Jetzt verbindlich reservieren</button>'
            html += '</form>'
        else:
            html += '<p style="color: #94a3b8; font-style: italic;">🔒 Aktuell nicht verfügbar</p>'
        html += '</div>'
    html += '</div>'
    
    html += '<div class="footer">'
    html += '<a href="/widerruf" target="_blank">🔒 Einwilligung widerrufen</a>'
    html += '<span class="ds-link" onclick="document.getElementById(\'dsgvoModal\').style.display=\'flex\'">📄 Datenschutzerklärung</span>'
    html += '<span class="ds-link" onclick="document.getElementById(\'haftungModal\').style.display=\'flex\'">⚠️ Haftungsausschluss</span>'
    html += '<a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter-Login</a>'
    html += '</div>'
    
    html += '<script>'
    html += 'function validateForm(form) {'
    html += 'const dsgvo = form.querySelector(\'input[name="dsgvo"]\');'
    html += 'if (!dsgvo.checked) { alert(\'Bitte stimmen Sie der Datenschutzerklärung zu.\'); return false; }'
    html += 'const haftung = form.querySelector(\'input[name="haftung"]\');'
    html += 'if (!haftung.checked) { alert(\'Bitte akzeptieren Sie den Haftungsausschluss.\'); return false; }'
    html += 'return true; }'
    html += 'window.onclick = function(event) {'
    html += 'const dsgvoModal = document.getElementById(\'dsgvoModal\');'
    html += 'const haftungModal = document.getElementById(\'haftungModal\');'
    html += 'if (event.target === dsgvoModal) { dsgvoModal.style.display = \'none\'; }'
    html += 'if (event.target === haftungModal) { haftungModal.style.display = \'none\'; } }'
    html += '</script>'
    html += '</body></html>'
    return html

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

@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    wartungen = Wartung.query.all()
    html = '<!DOCTYPE html><html><head><title>Mitarbeiter</title>'
    html += '<style>'
    html += 'body { font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; padding: 20px; }'
    html += '.header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }'
    html += '.header h1 { display: flex; align-items: center; gap: 10px; }'
    html += '.btn-logout { background: #ef4444; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 600; }'
    html += '.btn-logout:hover { background: #dc2626; }'
    html += '.tab { display: inline-block; padding: 10px 20px; cursor: pointer; background: #e2e8f0; border-radius: 8px 8px 0 0; margin-right: 4px; font-weight: 600; }'
    html += '.tab.active { background: white; color: #2563eb; }'
    html += '.tab-content { display: none; background: white; padding: 20px; border-radius: 0 8px 8px 8px; border: 1px solid #e2e8f0; }'
    html += '.tab-content.active { display: block; }'
    html += 'table { width: 100%; border-collapse: collapse; margin-top: 20px; }'
    html += 'th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; }'
    html += 'th { background: #f1f5f9; font-weight: 700; }'
    html += '.btn { padding: 5px 12px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; color: white; display: inline-block; font-size: 0.8rem; font-weight: 600; }'
    html += '.btn-edit { background: #2563eb; }'
    html += '.btn-del { background: #ef4444; }'
    html += '.btn-qr { background: #000; }'
    html += '.btn-add { background: #16a34a; }'
    html += '.btn-wartung { background: #f59e0b; }'
    html += '.form-box { background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0; }'
    html += '.form-box input, .form-box textarea, .form-box select { padding: 8px 12px; border: 2px solid #e2e8f0; border-radius: 6px; margin-right: 5px; margin-bottom: 8px; }'
    html += '.form-box textarea { width: 100%; min-height: 80px; }'
    html += '.badge { padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; display: inline-block; }'
    html += '.verfuegbar { background: #dcfce7; color: #166534; }'
    html += '.reserviert { background: #fef3c7; color: #92400e; }'
    html += '.wartung { background: #fee2e2; color: #991b1b; }'
    html += '.offen { background: #fee2e2; color: #991b1b; }'
    html += '.inbearbeitung { background: #fef3c7; color: #92400e; }'
    html += '.erledigt { background: #dcfce7; color: #166534; }'
    html += '@media (max-width: 640px) { .header { flex-direction: column; text-align: center; gap: 10px; } table { font-size: 0.8rem; } th, td { padding: 6px; } }'
    html += '</style></head><body>'
    html += f'<div class="header"><h1>🔧 Mitarbeiter Dashboard</h1><a href="/logout" class="btn-logout">Logout</a></div>'
    html += '<a href="/">← Zurück zur Kundenansicht</a><br><br>'
    html += f'<div class="tab active" onclick="showTab(\'fahrraeder\')">🚲 Fahrräder</div>'
    html += f'<div class="tab" onclick="showTab(\'kunden\')">👤 Kunden ({len(kunden)})</div>'
    html += f'<div class="tab" onclick="showTab(\'wartungen\')">🔧 Wartungen ({len(wartungen)})</div>'
    
    html += '<div id="tab-fahrraeder" class="tab-content active">'
    html += '<div class="form-box"><h3>➕ Neues Fahrrad anlegen</h3>'
    html += '<form action="/mitarbeiter/add" method="POST">'
    html += 'Nr: <input type="text" name="interne_nummer" required>'
    html += 'Marke: <input type="text" name="marke" required>'
    html += 'Modell: <input type="text" name="modell" required>'
    html += 'Größe: <input type="text" name="rahmengroesse">'
    html += 'Farbe: <input type="text" name="farbe">'
    html += 'Standort: <input type="text" name="standort">'
    html += '<button type="submit" class="btn btn-add">Hinzufügen</button>'
    html += '</form></div>'
    html += '<h3>📋 Alle Fahrräder</h3><table><tr><th>Nr</th><th>Marke</th><th>Modell</th><th>Status</th><th>Standort</th><th>Aktionen</th></tr>'
    for rad in raeder:
        status_class = rad.status.lower() if rad.status else 'verfuegbar'
        html += f'<tr><td>{rad.interne_nummer}</td><td>{rad.marke}</td><td>{rad.modell}</td><td><span class="badge {status_class}">{rad.status}</span></td><td>{rad.standort}</td><td><a href="/qr/{rad.id}" class="btn btn-qr" target="_blank">QR</a><a href="/rad/{rad.id}" class="btn btn-wartung">Historie</a><a href="/mitarbeiter/delete/{rad.id}" class="btn btn-del" onclick="return confirm(\'Sicher löschen?\')">Löschen</a></td></tr>'
    html += '</table></div>'
    
    html += '<div id="tab-kunden" class="tab-content"><h3>👤 Kunden mit Einwilligung</h3><table><tr><th>Name</th><th>Email</th><th>Adresse</th><th>DSGVO</th><th>Haftung</th><th>Datum</th></tr>'
    for k in kunden:
        html += f'<tr><td>{k.name}</td><td>{k.email}</td><td>{k.adresse}, {k.plz_ort}</td><td>{"✅" if k.einwilligung_dsgvo else "❌"}</td><td>{"✅" if k.haftungsausschluss_akzeptiert else "❌"}</td><td>{k.einwilligung_datum.strftime("%d.%m.%Y %H:%M") if k.einwilligung_datum else "-"}</td></tr>'
    html += '</table></div>'
    
    html += '<div id="tab-wartungen" class="tab-content"><h3>🔧 Alle Wartungen</h3><table><tr><th>Fahrrad</th><th>Mitarbeiter</th><th>Problem</th><th>Status</th><th>Datum</th><th>Aktionen</th></tr>'
    for w in wartungen:
        status_class = 'offen' if w.status == 'Offen' else 'inbearbeitung' if w.status == 'In Bearbeitung' else 'erledigt'
        problem_text = w.problem[:50] + ('...' if len(w.problem) > 50 else '')
        html += f'<tr><td>{w.fahrrad_id}</td><td>{w.mitarbeiter}</td><td>{problem_text}</td><td><span class="badge {status_class}">{w.status}</span></td><td>{w.erstellt_am.strftime("%d.%m.%Y %H:%M")}</td><td><a href="/wartung/{w.id}/edit" class="btn btn-edit">Bearbeiten</a></td></tr>'
    html += '</table></div>'
    
    html += '<script>'
    html += 'function showTab(tab) {'
    html += 'document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));'
    html += 'document.querySelectorAll(".tab").forEach(el => el.classList.remove("active"));'
    html += 'document.getElementById("tab-" + tab).classList.add("active");'
    html += 'event.target.classList.add("active"); }'
    html += '</script>'
    html += '</body></html>'
    return html

@app.route('/mitarbeiter/add', methods=['POST'])
@login_required
def add_rad():
    rad = Fahrrad(
        interne_nummer=request.form['interne_nummer'],
        marke=request.form['marke'],
        modell=request.form['modell'],
       
