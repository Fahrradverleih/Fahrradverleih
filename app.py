from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import qrcode
from io import BytesIO
import base64
PUBLIC_URL = os.environ.get('PUBLIC_URL', 'https://fahrradverleih.onrender.com')

app = Flask(__name__)

app.config['SECRET_KEY'] = 'geheimer_schluessel'
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
        .btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0069d9; }
        .verfuegbar { color: green; font-weight: bold; }
        .reserviert { color: orange; font-weight: bold; }
        .wartung { color: red; font-weight: bold; }
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
            <p><strong>{rad.interne_nummer}</strong> - {rad.marke} {rad.modell} - {rad.status}</p>
            <a href="/qr/{rad.id}" class="btn">📱 QR-Code</a>
        </div>
        """

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
        </div>
        """
    html += "</body></html>"
    return html
@app.route('/qr/<int:id>')
def show_qr(id):
    rad = Fahrrad.query.get(id)
    if not rad:
        return "Nicht gefunden", 404
    import qrcode
    from io import BytesIO
    import base64
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
