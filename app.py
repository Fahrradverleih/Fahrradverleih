from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'geheimer_schluessel_12345'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USERNAME = "chef"
ADMIN_PASSWORD = "geheim123"

class Fahrrad(db.Model):
    __tablename__ = 'fahrrad'
    id = db.Column(db.Integer, primary_key=True)
    interne_nummer = db.Column(db.String(20), unique=True, nullable=False)
    marke = db.Column(db.String(50), nullable=False)
    modell = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Verfügbar')

@app.route('/')
def index():
    try:
        raeder = Fahrrad.query.all()
        html = "<h1>🚲 Fahrradverleih</h1>"
        for rad in raeder:
            html += f"<p>{rad.marke} {rad.modell} - {rad.status}</p>"
        html += '<br><a href="/mitarbeiter">Mitarbeiter-Login</a>'
        return html
    except Exception as e:
        return f"<h1>Fehler bei der Datenbankverbindung</h1><p>{str(e)}</p><p>Bitte überprüfe die DATABASE_URL in Render.</p>"

@app.route('/mitarbeiter')
def mitarbeiter():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    raeder = Fahrrad.query.all()
    html = "<h1>🔧 Mitarbeiter</h1><a href='/logout'>Logout</a><hr>"
    for rad in raeder:
        html += f"<p>{rad.marke} {rad.modell} - {rad.status}</p>"
    return html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('mitarbeiter'))
        else:
            return "Falscher Name oder Passwort! <a href='/login'>Zurück</a>"
    return """
    <h2>Login</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Benutzername" required>
        <input type="password" name="password" placeholder="Passwort" required>
        <button type="submit">Einloggen</button>
    </form>
    """

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
