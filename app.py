from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import sqlite3
import os


DB = 'solicitudes.db'

# Simple in-memory session store
sessions = {}

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# --- DB helpers ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
      CREATE TABLE IF NOT EXISTS solicitudes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nombre TEXT,
      correo TEXT,
      tipo TEXT,
      inicio TEXT,
      fin TEXT,
      motivo TEXT,
      estado TEXT,
      creado_en TEXT
    )
''')
    conn.commit()
    conn.close()

init_db()


# --- Utilidades simples ---


def parse_date(s):
  for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
    try:
        return datetime.strptime(s, fmt).date()
    except Exception:
      continue
  return None


# Minimal intent handler (rules)
def handle_message(state, message):
  # state is a dict with progress fields
  # This is extremely simple and deterministic
  msg = message.strip().lower()

  # If no nombre, ask for nombre
  if not state.get('nombre'):
    # try to extract email-like token
    if '@' in msg and ' ' not in msg:
      state['correo'] = msg
      return {'reply': 'Gracias. Ahora dime tu nombre completo.', 'state': state}
    # if user writes name
    state['nombre'] = message.strip()
    return {'reply': '¿Cuál es tu correo electrónico?', 'state': state}


  if not state.get('correo'):
    if '@' in msg:
      state['correo'] = message.strip()
      return {'reply': '¿Qué tipo de permiso requieres? (p. ej. Enfermedad, Personal, Estudio)', 'state': state}
    else:
      return {'reply': 'Ese correo no parece válido. Por favor escribe tu correo (ej: tu@dominio.com).', 'state': state}


  if not state.get('tipo'):
    state['tipo'] = message.strip().title()
    return {'reply': '¿Fecha de inicio? (AAAA-MM-DD)', 'state': state}


  if not state.get('inicio'):
    d = parse_date(message.strip())
    if d:
      state['inicio'] = d.isoformat()
      return {'reply': '¿Fecha de fin? (AAAA-MM-DD)', 'state': state}
    else:
      return {'reply': 'No pude entender la fecha. Usa el formato AAAA-MM-DD o DD/MM/AAAA.', 'state': state}


  if not state.get('fin'):
    d = parse_date(message.strip())
    if d:
      # validate fin >= inicio
      inicio = parse_date(state['inicio'])
      if d < inicio:
        return {'reply': 'La fecha de fin es anterior a la fecha de inicio. Por favor ingresa una fecha de fin válida.', 'state': state}
      state['fin'] = d.isoformat()
      return {'reply': 'Cuéntame el motivo del permiso.', 'state': state}
    else:
      return {'reply': 'No pude entender la fecha. Usa el formato AAAA-MM-DD o DD/MM/AAAA.', 'state': state}


  if not state.get('motivo'):
    state['motivo'] = message.strip()
    # Build summary
    summary = (
      f"Resumen:\nNombre: {state['nombre']}\nCorreo: {state['correo']}\nTipo: {state['tipo']}\nInicio: {state['inicio']}\nFin: {state['fin']}\nMotivo: {state['motivo']}"
    )
    return {'reply': summary + '\n\n¿Confirmas enviar la solicitud? (si/no)', 'state': state}


# Confirmation
  if state.get('motivo') and not state.get('confirmado'):
    if msg in ('si', 'sí', 's', 'yes'):
      # save to DB
      conn = sqlite3.connect(DB)
      c = conn.cursor()
      c.execute('''INSERT INTO solicitudes (nombre, correo, tipo, inicio, fin, motivo, estado, creado_en)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (
        state['nombre'], state['correo'], state['tipo'], state['inicio'], state['fin'], state['motivo'], 'Pendiente', datetime.utcnow().isoformat()
      ))
      conn.commit()
      solicitud_id = c.lastrowid
      conn.close()
      state['confirmado'] = True
      return {'reply': 'Tu solicitud ha sido registrada con éxito. Número de solicitud: ' + str(solicitud_id), 'state': state}
    else:
      return {'reply': 'Solicitud cancelada. Si quieres empezar de nuevo, escribe "reiniciar".', 'state': state}

  # Fallback
  return {'reply': 'No entendí. Por favor sigue las indicaciones.', 'state': state}


# --- Flask routes ---

@app.route('/')
def index():
    return send_file('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    message = data.get('message', '').strip()

    # Handle reset
    if message.lower() in ('reiniciar', 'reset', 'empezar'):
        sessions[session_id] = {}
        return jsonify({'reply': 'Conversación reiniciada. Por favor dime tu nombre completo.'})

    # Get or create session state
    if session_id not in sessions:
        sessions[session_id] = {}

    state = sessions[session_id]
    result = handle_message(state, message)
    sessions[session_id] = result['state']

    return jsonify({'reply': result['reply']})


if __name__ == '__main__':
    app.run(debug=True, port=5000)