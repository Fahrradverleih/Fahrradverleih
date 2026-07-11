@app.route('/')
def kundenansicht():
    raeder = Fahrrad.query.all()
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>🚲 Fahrradverleih</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; padding: 20px; }
        .header { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; padding: 30px 20px; border-radius: 16px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .header h1 { font-size: 2rem; display: flex; align-items: center; gap: 10px; }
        .header .sub { font-size: 0.9rem; opacity: 0.9; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 24px; }
        .card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); transition: transform 0.2s; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; text-transform: uppercase; }
        .verfuegbar { background: #dcfce7; color: #166534; }
        .reserviert { background: #fef3c7; color: #92400e; }
        .wartung { background: #fee2e2; color: #991b1b; }
        .footer { margin-top: 40px; text-align: center; font-size: 0.85rem; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 20px; }
        .footer a { color: #2563eb; text-decoration: none; font-weight: 600; }
        .footer a:hover { color: #7c3aed; text-decoration: underline; }
        .logo-img { font-size: 2.5rem; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 12px; }
        @media (max-width: 640px) {
            .header { flex-direction: column; text-align: center; }
            .header h1 { font-size: 1.5rem; }
            .grid { grid-template-columns: 1fr; }
        }
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
        
        <div class="grid">
    """
    for rad in raeder:
        html += f"""
            <div class="card">
                <h3>🚲 {rad.marke} {rad.modell}</h3>
                <p><strong>Nr:</strong> {rad.interne_nummer}<br>
                <strong>Größe:</strong> {rad.rahmengroesse} / {rad.farbe}<br>
                <strong>Standort:</strong> {rad.standort}</p>
                <span class="badge {rad.status.lower()}">{rad.status}</span>
            </div>
        """
    html += """
        </div>
        <div class="footer">
            <a href="/mitarbeiter" target="_blank">🔐 Mitarbeiter-Login</a>
        </div>
    </body>
    </html>
    """
    return html
