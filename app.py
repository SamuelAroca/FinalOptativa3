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

  # Check for menu options at any time (not in the middle of creating a request)
  if not state.get('nombre') or state.get('confirmado'):
    # Menu options
    if msg in ('1', 'nueva', 'nueva solicitud', 'otro permiso'):
      # Reset state for new request
      state.clear()
      return {'reply': 'Perfecto, iniciemos una nueva solicitud. Por favor dime tu nombre completo.', 'state': state}
    elif msg in ('2', 'consultar', 'ver solicitud', 'estado', 'consultar solicitud'):
      state.clear()
      state['action'] = 'consultar'
      state['next_action'] = True
      
      # Mostrar las últimas solicitudes como ayuda
      conn = sqlite3.connect(DB)
      c = conn.cursor()
      c.execute('SELECT id, nombre, tipo, estado FROM solicitudes ORDER BY id DESC LIMIT 10')
      rows = c.fetchall()
      conn.close()
      
      if rows:
        mensaje = '📋 **Últimas solicitudes registradas:**\n\n'
        for row in rows:
          mensaje += f"#{row[0]} - {row[1]} ({row[2]}) - {row[3]}\n"
        mensaje += '\n💡 Escribe el número de solicitud que deseas consultar:'
        return {'reply': mensaje, 'state': state}
      else:
        return {'reply': 'No hay solicitudes registradas aún. Por favor ingresa el número de solicitud que deseas consultar:', 'state': state}
    elif msg in ('3', 'mis solicitudes', 'todas', 'listar', 'ver todas'):
      state.clear()
      state['action'] = 'listar'
      state['next_action'] = True
      return {'reply': 'Por favor ingresa tu correo electrónico para ver todas tus solicitudes:', 'state': state}
    elif msg in ('4', 'salir', 'terminar', 'adios', 'chao'):
      state.clear()
      return {'reply': '¡Hasta pronto! Gracias por usar el sistema de solicitudes. Si necesitas algo más, solo escribe "hola" para comenzar.', 'state': state}

  # Handle consultar solicitud
  if state.get('action') == 'consultar' and state.get('next_action'):
    try:
      solicitud_id = int(msg)
      conn = sqlite3.connect(DB)
      c = conn.cursor()
      c.execute('SELECT * FROM solicitudes WHERE id = ?', (solicitud_id,))
      row = c.fetchone()
      conn.close()
      
      if row:
        resultado = f"📋 **Solicitud #{row[0]}**\n\n" \
                   f"👤 Nombre: {row[1]}\n" \
                   f"📧 Correo: {row[2]}\n" \
                   f"📝 Tipo: {row[3]}\n" \
                   f"📅 Inicio: {row[4]}\n" \
                   f"📅 Fin: {row[5]}\n" \
                   f"💬 Motivo: {row[6]}\n" \
                   f"🔔 Estado: {row[7]}\n" \
                   f"🕐 Creado: {row[8]}\n\n" \
                   f"¿Qué deseas hacer?\n" \
                   f"1️⃣ Nueva solicitud\n" \
                   f"2️⃣ Consultar otra solicitud\n" \
                   f"3️⃣ Ver todas mis solicitudes\n" \
                   f"4️⃣ Salir"
        state.clear()
        state['confirmado'] = True
        return {'reply': resultado, 'state': state}
      else:
        # Mostrar las solicitudes disponibles
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT id, nombre, tipo, estado FROM solicitudes ORDER BY id DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        
        if rows:
          resultado = f'❌ No se encontró la solicitud #{solicitud_id}.\n\n📋 **Últimas 10 solicitudes registradas:**\n\n'
          for row in rows:
            resultado += f"#{row[0]} - {row[1]} ({row[2]}) - {row[3]}\n"
          resultado += f"\n💡 Escribe el número de solicitud que deseas consultar, o:\n" \
                      f"1️⃣ Nueva solicitud\n" \
                      f"3️⃣ Ver todas mis solicitudes (por correo)\n" \
                      f"4️⃣ Salir"
          return {'reply': resultado, 'state': state}
        else:
          resultado = f'❌ No se encontró la solicitud #{solicitud_id} y no hay solicitudes registradas.\n\n' \
                     f'¿Qué deseas hacer?\n' \
                     f'1️⃣ Crear nueva solicitud\n' \
                     f'4️⃣ Salir'
          state.clear()
          state['confirmado'] = True
          return {'reply': resultado, 'state': state}
    except ValueError:
      return {'reply': 'Por favor ingresa un número válido de solicitud:', 'state': state}

  # Handle listar solicitudes
  if state.get('action') == 'listar' and state.get('next_action'):
    if '@' in msg:
      correo = message.strip()
      conn = sqlite3.connect(DB)
      c = conn.cursor()
      c.execute('SELECT * FROM solicitudes WHERE correo = ? ORDER BY id DESC', (correo,))
      rows = c.fetchall()
      conn.close()
      
      if rows:
        resultado = f"📬 **Solicitudes encontradas para {correo}:**\n\n"
        for row in rows:
          resultado += f"#{row[0]} - {row[3]} ({row[4]} al {row[5]}) - Estado: {row[7]}\n"
        resultado += f"\n¿Qué deseas hacer?\n" \
                    f"1️⃣ Nueva solicitud\n" \
                    f"2️⃣ Consultar solicitud específica\n" \
                    f"3️⃣ Ver todas mis solicitudes\n" \
                    f"4️⃣ Salir"
        state.clear()
        state['confirmado'] = True
        return {'reply': resultado, 'state': state}
      else:
        resultado = f'No se encontraron solicitudes para el correo {correo}.\n\n¿Qué deseas hacer?\n1️⃣ Nueva solicitud\n2️⃣ Consultar solicitud\n3️⃣ Intentar con otro correo\n4️⃣ Salir'
        state.clear()
        state['confirmado'] = True
        return {'reply': resultado, 'state': state}
    else:
      return {'reply': 'Por favor ingresa un correo válido (debe contener @):', 'state': state}

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
      menu = f"✅ ¡Tu solicitud ha sido registrada con éxito!\n\n" \
             f"📋 **Número de solicitud: {solicitud_id}**\n\n" \
             f"Guarda este número para consultar el estado de tu solicitud.\n\n" \
             f"¿Qué deseas hacer ahora?\n" \
             f"1️⃣ Crear nueva solicitud\n" \
             f"2️⃣ Consultar una solicitud\n" \
             f"3️⃣ Ver todas mis solicitudes\n" \
             f"4️⃣ Salir\n\n" \
             f"Escribe el número o la opción que prefieras."
      return {'reply': menu, 'state': state}
    else:
      state.clear()
      return {'reply': 'Solicitud cancelada. Si quieres empezar de nuevo, escribe tu nombre.', 'state': state}

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
    if message.lower() in ('reiniciar', 'reset', 'empezar', 'hola', 'inicio', 'menu'):
        sessions[session_id] = {}
        return jsonify({'reply': '¡Hola! Bienvenido al sistema de solicitudes de permisos.\n\n¿Qué deseas hacer?\n\n1️⃣ Crear nueva solicitud\n2️⃣ Consultar una solicitud (muestra las últimas)\n3️⃣ Ver todas mis solicitudes (por correo)\n\n💡 Tip: Si no sabes el número de tu solicitud, usa la opción 3 con tu correo.'})

    # Get or create session state
    if session_id not in sessions:
        sessions[session_id] = {}

    state = sessions[session_id]
    result = handle_message(state, message)
    sessions[session_id] = result['state']

    return jsonify({'reply': result['reply']})


@app.route('/admin')
def admin():
    return send_file('admin.html')


@app.route('/api/solicitudes', methods=['GET'])
def get_solicitudes():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM solicitudes ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    
    solicitudes = [dict(row) for row in rows]
    return jsonify(solicitudes)


@app.route('/api/solicitudes/<int:solicitud_id>', methods=['PUT'])
def update_solicitud(solicitud_id):
    data = request.json
    nuevo_estado = data.get('estado')
    
    if nuevo_estado not in ['Pendiente', 'Aprobado', 'Rechazado']:
        return jsonify({'error': 'Estado inválido'}), 400
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('UPDATE solicitudes SET estado = ? WHERE id = ?', (nuevo_estado, solicitud_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Solicitud {solicitud_id} actualizada a {nuevo_estado}'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)