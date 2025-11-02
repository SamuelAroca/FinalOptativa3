from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from dotenv import load_dotenv
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Cargar variables de entorno
load_dotenv()

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
      creado_en TEXT,
      comentarios TEXT
    )
''')
    conn.commit()
    conn.close()

init_db()


# --- Email configuration ---
def send_email_notification(to_email, subject, body, pdf_path=None):
    """
    Envía correo electrónico real usando SMTP.
    """
    # Obtener configuración desde variables de entorno
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    sender_name = os.getenv('SENDER_NAME', 'Sistema de Solicitudes')
    
    # Validar que las credenciales estén configuradas
    if not sender_email or not sender_password or sender_password == 'tu_contraseña_aqui':
        return False
    
    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Agregar cuerpo del mensaje
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Adjuntar PDF si existe
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(pdf_path)}"
            )
            msg.attach(part)
        
        # Conectar y enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        return False
    except Exception as e:
        return False


def generate_pdf(solicitud_data):
    """Genera un PDF con los detalles de la solicitud"""
    if not os.path.exists('pdfs'):
        os.makedirs('pdfs')
    
    filename = f"pdfs/solicitud_{solicitud_data['id']}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=1
    )
    
    # Título
    title = Paragraph("📋 SOLICITUD DE PERMISO", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Datos de la solicitud en tabla
    data = [
        ['Campo', 'Valor'],
        ['Número de Solicitud', f"#{solicitud_data['id']}"],
        ['Nombre Completo', solicitud_data['nombre']],
        ['Correo Electrónico', solicitud_data['correo']],
        ['Tipo de Permiso', solicitud_data['tipo']],
        ['Fecha de Inicio', solicitud_data['inicio']],
        ['Fecha de Fin', solicitud_data['fin']],
        ['Motivo', solicitud_data['motivo']],
        ['Estado', solicitud_data['estado']],
        ['Fecha de Creación', solicitud_data['creado_en']],
    ]
    
    table = Table(data, colWidths=[2.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Nota al pie
    note = Paragraph(
        "<i>Este documento es un comprobante de tu solicitud de permiso. "
        "Guárdalo para futuras referencias.</i>",
        styles['Normal']
    )
    elements.append(note)
    
    doc.build(elements)
    return filename


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
    elif msg in ('cancelar', 'cancelar solicitud', 'anular'):
      state.clear()
      state['action'] = 'cancelar'
      state['next_action'] = True
      return {'reply': 'Para cancelar una solicitud, por favor ingresa tu correo electrónico:', 'state': state}
    elif msg in ('4', 'salir', 'terminar', 'adios', 'chao'):
      state.clear()
      return {'reply': '¡Hasta pronto! Gracias por usar el sistema de solicitudes. Si necesitas algo más, solo escribe "hola" para comenzar.', 'state': state}
    elif msg in ('estadisticas', 'estadísticas', 'stats', 'mis estadisticas'):
      state.clear()
      state['action'] = 'estadisticas'
      state['next_action'] = True
      return {'reply': 'Para ver tus estadísticas, por favor ingresa tu correo electrónico:', 'state': state}

  # Handle estadisticas
  if state.get('action') == 'estadisticas' and state.get('next_action'):
    if '@' in msg:
      correo = message.strip()
      conn = sqlite3.connect(DB)
      c = conn.cursor()
      
      # Contar solicitudes por estado
      c.execute('SELECT COUNT(*) FROM solicitudes WHERE correo = ?', (correo,))
      total = c.fetchone()[0]
      
      c.execute('SELECT COUNT(*) FROM solicitudes WHERE correo = ? AND estado = "Pendiente"', (correo,))
      pendientes = c.fetchone()[0]
      
      c.execute('SELECT COUNT(*) FROM solicitudes WHERE correo = ? AND estado = "Aprobado"', (correo,))
      aprobadas = c.fetchone()[0]
      
      c.execute('SELECT COUNT(*) FROM solicitudes WHERE correo = ? AND estado = "Rechazado"', (correo,))
      rechazadas = c.fetchone()[0]
      
      c.execute('SELECT COUNT(*) FROM solicitudes WHERE correo = ? AND estado = "Cancelado"', (correo,))
      canceladas = c.fetchone()[0]
      
      # Solicitud más reciente
      c.execute('SELECT tipo, inicio, estado FROM solicitudes WHERE correo = ? ORDER BY id DESC LIMIT 1', (correo,))
      reciente = c.fetchone()
      
      conn.close()
      
      if total > 0:
        tasa_aprobacion = (aprobadas / total * 100) if total > 0 else 0
        
        resultado = f"📊 **ESTADÍSTICAS PARA {correo}**\n\n" \
                   f"📈 Total de solicitudes: {total}\n" \
                   f"⏳ Pendientes: {pendientes}\n" \
                   f"✅ Aprobadas: {aprobadas}\n" \
                   f"❌ Rechazadas: {rechazadas}\n" \
                   f"🚫 Canceladas: {canceladas}\n\n" \
                   f"📊 Tasa de aprobación: {tasa_aprobacion:.1f}%\n\n"
        
        if reciente:
          resultado += f"🕐 Última solicitud:\n" \
                      f"   • Tipo: {reciente[0]}\n" \
                      f"   • Fecha: {reciente[1]}\n" \
                      f"   • Estado: {reciente[2]}\n\n"
        
        resultado += f"¿Qué deseas hacer?\n" \
                    f"1️⃣ Nueva solicitud\n" \
                    f"2️⃣ Consultar solicitud\n" \
                    f"3️⃣ Ver todas mis solicitudes\n" \
                    f"4️⃣ Salir"
        
        state.clear()
        state['confirmado'] = True
        return {'reply': resultado, 'state': state}
      else:
        state.clear()
        state['confirmado'] = True
        return {'reply': f'No tienes solicitudes registradas con el correo {correo}.\n\n¿Deseas crear una nueva solicitud? (1 = Sí, 4 = Salir)', 'state': state}
    else:
      return {'reply': 'Por favor ingresa un correo válido (debe contener @):', 'state': state}

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

  # Handle cancelar solicitud
  if state.get('action') == 'cancelar':
    if not state.get('cancel_correo'):
      if '@' in msg:
        correo = message.strip()
        state['cancel_correo'] = correo
        
        # Buscar solicitudes pendientes del usuario
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT id, tipo, inicio, fin FROM solicitudes WHERE correo = ? AND estado = "Pendiente" ORDER BY id DESC', (correo,))
        rows = c.fetchall()
        conn.close()
        
        if rows:
          resultado = f"📋 **Solicitudes pendientes para {correo}:**\n\n"
          for row in rows:
            resultado += f"#{row[0]} - {row[1]} ({row[2]} al {row[3]})\n"
          resultado += f"\n💡 Escribe el número de la solicitud que deseas cancelar:"
          return {'reply': resultado, 'state': state}
        else:
          state.clear()
          state['confirmado'] = True
          return {'reply': f'No se encontraron solicitudes pendientes para {correo}.\n\n¿Qué deseas hacer?\n1️⃣ Nueva solicitud\n2️⃣ Consultar solicitud\n3️⃣ Ver todas mis solicitudes\n4️⃣ Salir', 'state': state}
      else:
        return {'reply': 'Por favor ingresa un correo válido (debe contener @):', 'state': state}
    else:
      # Usuario ya proporcionó correo, ahora esperamos el ID
      try:
        solicitud_id = int(msg)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT * FROM solicitudes WHERE id = ? AND correo = ? AND estado = "Pendiente"', (solicitud_id, state['cancel_correo']))
        row = c.fetchone()
        
        if row:
          c.execute('UPDATE solicitudes SET estado = ? WHERE id = ?', ('Cancelado', solicitud_id))
          conn.commit()
          conn.close()
          
          # Enviar notificación
          subject = f"❌ Solicitud #{solicitud_id} - Cancelada"
          body = f"""Hola,

Tu solicitud de permiso #{solicitud_id} ha sido cancelada exitosamente.

Si deseas crear una nueva solicitud, puedes hacerlo en cualquier momento.

Saludos,
Sistema de Gestión de Permisos"""
          send_email_notification(state['cancel_correo'], subject, body)
          
          state.clear()
          state['confirmado'] = True
          return {'reply': f'✅ La solicitud #{solicitud_id} ha sido cancelada exitosamente.\n\n📧 Se ha enviado una confirmación por correo.\n\n¿Qué deseas hacer?\n1️⃣ Nueva solicitud\n2️⃣ Consultar solicitud\n3️⃣ Ver todas mis solicitudes\n4️⃣ Salir', 'state': state}
        else:
          conn.close()
          return {'reply': f'❌ No se encontró una solicitud pendiente con el número {solicitud_id} para tu correo. Verifica el número e intenta de nuevo:', 'state': state}
      except ValueError:
        return {'reply': 'Por favor ingresa un número válido:', 'state': state}

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
    if '@' in msg and '.' in msg.split('@')[-1]:
      state['correo'] = message.strip()
      return {'reply': '¿Qué tipo de permiso requieres?\n\n💡 Ejemplos:\n• Enfermedad 🏥\n• Personal 👤\n• Estudio 📚\n• Vacaciones 🏖️\n• Familiar 👨‍👩‍👧\n• Otro (especifica)', 'state': state}
    else:
      return {'reply': 'Ese correo no parece válido. Por favor escribe un correo válido (ej: usuario@dominio.com).', 'state': state}


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
    state['esperando_confirmacion'] = True  # Nueva bandera
    # Build summary
    summary = (
      f"Resumen:\nNombre: {state['nombre']}\nCorreo: {state['correo']}\nTipo: {state['tipo']}\nInicio: {state['inicio']}\nFin: {state['fin']}\nMotivo: {state['motivo']}"
    )
    return {'reply': summary + '\n\n¿Confirmas enviar la solicitud? (si/no)', 'state': state}


# Confirmation - primera pregunta (¿confirmas enviar?)
  if state.get('esperando_confirmacion') and not state.get('solicitud_guardada'):
    if msg in ('si', 'sí', 's', 'yes'):
      # save to DB
      conn = sqlite3.connect(DB)
      c = conn.cursor()
      c.execute('''INSERT INTO solicitudes (nombre, correo, tipo, inicio, fin, motivo, estado, creado_en)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (
        state['nombre'], state['correo'], state['tipo'], state['inicio'], state['fin'], state['motivo'], 'Pendiente', datetime.now().isoformat()
      ))
      conn.commit()
      solicitud_id = c.lastrowid
      conn.close()
      state['solicitud_id'] = solicitud_id
      state['solicitud_guardada'] = True  # Marcar que ya se guardó
      state['esperando_confirmacion'] = False  # Ya no está esperando la primera confirmación
      state['esperando_respuesta_correo'] = True  # Ahora espera respuesta del correo
      return {'reply': f"✅ ¡Tu solicitud ha sido registrada con éxito!\n\n📋 **Número de solicitud: {solicitud_id}**\n\n¿Deseas recibir un resumen en PDF por correo electrónico? (si/no)", 'state': state}
    else:
      state.clear()
      return {'reply': 'Solicitud cancelada. Si quieres empezar de nuevo, escribe tu nombre.', 'state': state}

  # Segunda pregunta (¿quieres recibir correo?)
  if state.get('esperando_respuesta_correo') and state.get('solicitud_guardada') and not state.get('confirmado'):
    if msg in ('si', 'sí', 's', 'yes'):
      # Generar PDF y enviar correo
      conn = sqlite3.connect(DB)
      conn.row_factory = sqlite3.Row
      c = conn.cursor()
      c.execute('SELECT * FROM solicitudes WHERE id = ?', (state['solicitud_id'],))
      row = c.fetchone()
      conn.close()
      
      if row:
        solicitud = dict(row)
        pdf_file = generate_pdf(solicitud)
        
        # Enviar correo con PDF
        subject = f"Solicitud de Permiso #{solicitud['id']} - Confirmación"
        body = f"""Hola {solicitud['nombre']},

Tu solicitud de permiso ha sido registrada exitosamente.

Detalles:
- Número de solicitud: #{solicitud['id']}
- Tipo: {solicitud['tipo']}
- Fecha inicio: {solicitud['inicio']}
- Fecha fin: {solicitud['fin']}
- Estado: {solicitud['estado']}

Adjunto encontrarás un PDF con el resumen completo de tu solicitud.

Puedes consultar el estado de tu solicitud en cualquier momento usando el número proporcionado.

Saludos,
Sistema de Gestión de Permisos"""
        
        send_email_notification(solicitud['correo'], subject, body, pdf_file)
        
        state['confirmado'] = True
        menu = f"📧 ¡Perfecto! Se ha enviado un resumen en PDF a {solicitud['correo']}\n\n" \
               f"📬 Revisa tu bandeja de entrada (puede tardar 1-2 minutos).\n" \
               f"💡 Si no lo ves, revisa la carpeta de Spam.\n\n" \
               f"📋 Recuerda tu número de solicitud: **#{state['solicitud_id']}**\n\n" \
               f"¿Qué deseas hacer ahora?\n" \
               f"1️⃣ Crear nueva solicitud\n" \
               f"2️⃣ Consultar una solicitud\n" \
               f"3️⃣ Ver todas mis solicitudes\n" \
               f"📊 Ver mis estadísticas\n" \
               f"4️⃣ Salir"
        return {'reply': menu, 'state': state}
    else:
      state['confirmado'] = True
      menu = f"✅ De acuerdo, no se enviará correo.\n\n" \
             f"📋 Guarda este número para consultar el estado: **#{state['solicitud_id']}**\n\n" \
             f"💡 Tip: Puedes consultar tu solicitud en cualquier momento con la opción 2.\n\n" \
             f"¿Qué deseas hacer ahora?\n" \
               f"1️⃣ Crear nueva solicitud\n" \
               f"2️⃣ Consultar una solicitud\n" \
               f"3️⃣ Ver todas mis solicitudes\n" \
               f"📊 Ver mis estadísticas\n" \
               f"4️⃣ Salir"
      return {'reply': menu, 'state': state}

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
        return jsonify({'reply': '¡Hola! 👋 Bienvenido al sistema de solicitudes de permisos.\n\n¿Qué deseas hacer?\n\n💡 Tip: Puedes usar los botones o escribir directamente tu nombre para crear una solicitud.'})

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
    
    # Obtener datos de la solicitud antes de actualizar
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM solicitudes WHERE id = ?', (solicitud_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    
    solicitud = dict(row)
    
    # Actualizar estado
    c.execute('UPDATE solicitudes SET estado = ? WHERE id = ?', (nuevo_estado, solicitud_id))
    conn.commit()
    conn.close()
    
    # Enviar notificación por correo
    if nuevo_estado in ['Aprobado', 'Rechazado']:
        estado_emoji = "✅" if nuevo_estado == "Aprobado" else "❌"
        subject = f"{estado_emoji} Solicitud de Permiso #{solicitud_id} - {nuevo_estado}"
        
        if nuevo_estado == 'Aprobado':
            body = f"""Hola {solicitud['nombre']},

¡Buenas noticias! Tu solicitud de permiso ha sido APROBADA.

Detalles de tu solicitud:
- Número de solicitud: #{solicitud['id']}
- Tipo de permiso: {solicitud['tipo']}
- Fecha inicio: {solicitud['inicio']}
- Fecha fin: {solicitud['fin']}
- Motivo: {solicitud['motivo']}

Tu permiso ha sido autorizado. Puedes proceder con tus planes.

Saludos,
Departamento de Recursos Humanos"""
        else:
            body = f"""Hola {solicitud['nombre']},

Lamentamos informarte que tu solicitud de permiso ha sido RECHAZADA.

Detalles de tu solicitud:
- Número de solicitud: #{solicitud['id']}
- Tipo de permiso: {solicitud['tipo']}
- Fecha inicio: {solicitud['inicio']}
- Fecha fin: {solicitud['fin']}
- Motivo: {solicitud['motivo']}

Si tienes preguntas sobre esta decisión, por favor contacta al Departamento de Recursos Humanos.

Saludos,
Departamento de Recursos Humanos"""
        
        send_email_notification(solicitud['correo'], subject, body)
    
    return jsonify({'success': True, 'message': f'Solicitud {solicitud_id} actualizada a {nuevo_estado}'})


@app.route('/api/solicitudes/<int:solicitud_id>/pdf', methods=['GET'])
def download_pdf(solicitud_id):
    """Endpoint para descargar el PDF de una solicitud"""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM solicitudes WHERE id = ?', (solicitud_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    
    solicitud = dict(row)
    pdf_file = generate_pdf(solicitud)
    
    return send_file(pdf_file, as_attachment=True, download_name=f'solicitud_{solicitud_id}.pdf')


if __name__ == '__main__':
    app.run(debug=True, port=5000)