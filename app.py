@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    raeder = Fahrrad.query.all()
    kunden = Kunde.query.all()
    wartungen = Wartung.query.all()
    html = '<!DOCTYPE html>'
    html += '<html><head><title>Mitarbeiter</title>'
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
    html += '</style>'
    html += '</head><body>'
    html += f'<div class="header"><h1>🔧 Mitarbeiter Dashboard</h1><a href="/logout" class="btn-logout">Logout</a></div>'
    html += '<a href="/">← Zurück zur Kundenansicht</a><br><br>'
    html += f'<div class="tab active" onclick="showTab(\'fahrraeder\')">🚲 Fahrräder</div>'
    html += f'<div class="tab" onclick="showTab(\'kunden\')">👤 Kunden ({len(kunden)})</div>'
    html += f'<div class="tab" onclick="showTab(\'wartungen\')">🔧 Wartungen ({len(wartungen)})</div>'
    
    # Tab: Fahrräder
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
    
    # Tab: Kunden
    html += '<div id="tab-kunden" class="tab-content"><h3>👤 Kunden mit Einwilligung</h3><table><tr><th>Name</th><th>Email</th><th>Adresse</th><th>DSGVO</th><th>Haftung</th><th>Datum</th></tr>'
    for k in kunden:
        html += f'<tr><td>{k.name}</td><td>{k.email}</td><td>{k.adresse}, {k.plz_ort}</td><td>{"✅" if k.einwilligung_dsgvo else "❌"}</td><td>{"✅" if k.haftungsausschluss_akzeptiert else "❌"}</td><td>{k.einwilligung_datum.strftime("%d.%m.%Y %H:%M") if k.einwilligung_datum else "-"}</td></tr>'
    html += '</table></div>'
    
    # Tab: Wartungen
    html += '<div id="tab-wartungen" class="tab-content"><h3>🔧 Alle Wartungen</h3><table><tr><th>Fahrrad</th><th>Mitarbeiter</th><th>Problem</th><th>Status</th><th>Datum</th><th>Aktionen</th></tr>'
    for w in wartungen:
        status_class = 'offen' if w.status == 'Offen' else 'inbearbeitung' if w.status == 'In Bearbeitung' else 'erledigt'
        html += f'<tr><td>{w.fahrrad_id}</td><td>{w.mitarbeiter}</td><td>{w.problem[:50]}{"..." if w.problem|length > 50 else ""}</td><td><span class="badge {status_class}">{w.status}</span></td><td>{w.erstellt_am.strftime("%d.%m.%Y %H:%M")}</td><td><a href="/wartung/{w.id}/edit" class="btn btn-edit">Bearbeiten</a></td></tr>'
    html += '</table></div>'
    
    html += '<script>'
    html += 'function showTab(tab) {'
    html += 'document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));'
    html += 'document.querySelectorAll(".tab").forEach(el => el.classList.remove("active"));'
    html += 'document.getElementById("tab-" + tab).classList
