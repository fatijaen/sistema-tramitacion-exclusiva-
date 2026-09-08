 prompt_sistema = f"""
    Eres un asistente virtual inclusivo de un hospital. Tu meta es ayudar a pacientes a pedir una cita médica.
    
    REGLAS CRÍTICAS DE IDIOMA E INCLUSIÓN:
    1. DETECCIÓN DE IDIOMA: Detecta en qué idioma te está hablando el usuario.
    2. RESPUESTA ADAPTADA: Responde SIEMPRE en el MISMO IDIOMA en el que te hable el usuario (si te habla en inglés, responde en inglés; si te habla en francés, en francés).
    3. LECTURA FÁCIL: Sin importar el idioma que uses, aplica siempre las reglas de 'Lectura Fácil': frases muy cortas, palabras muy simples, tono amable y sin tecnicismos médicos difíciles.
    4. DIGITALIZACIÓN: Extrae los datos clave para actualizar el formulario (el formulario interno siempre se guarda en español de fondo).
    
    ESTADO ACTUAL DEL FORMULARIO:
    {st.session_state.formulario}
# Configuración de la página web
st.set_page_config(page_title="Cita Médica Inclusiva", layout="wide", page_icon="🏥")

# Inicializar la API de OpenAI
# Recuerda configurar tu clave: export OPENAI_API_KEY="tu-clave" o ponerla aquí directamente
API_KEY = os.getenv("OPENAI_API_KEY", "TU_OPENAI_API_KEY_AQUI")
client = OpenAI(api_key=API_KEY)

# 1. ESTRUCTURA DEL FORMULARIO DE CITA
class FormularioCita(BaseModel):
    motivo_consulta: str = Field(default="", description="Síntoma o motivo en palabras simples.")
    especialidad: str = Field(default="", description="Medicina General, Pediatría o Enfermería.")
    preferencia_horario: str = Field(default="", description="Mañana, tarde o lo antes posible.")
    datos_completos: bool = Field(default=False, description="¿Están todos los datos listos?")

# Inicializar variables de estado de la sesión si no existen
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "motivo_consulta": "",
        "especialidad": "",
        "preferencia_horario": "",
        "datos_completos": False
    }
if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = [
        {"role": "assistant", "content": "¡Hola! Soy tu asistente de salud. Estoy aquí para ayudarte a pedir tu cita médica sin complicaciones. ¿Qué te ocurre o cómo te sientes hoy?"}
    ]
if "audio_generado" not in st.session_state:
    st.session_state.audio_generado = None

# FUNCIONES RELEVANTES DE IA
def procesar_con_ia(texto_usuario):
    """Envía la respuesta al modelo para actualizar el formulario y obtener respuesta en Lectura Fácil"""
    prompt_sistema = f"""
    Eres un asistente virtual inclusivo de un hospital. Tu meta es ayudar a pacientes (mayores, extranjeros o con dificultades) a pedir cita.
    
    REGLAS:
    1. Responde SIEMPRE en español con LECTURA FÁCIL (frases cortas, claras, sin tecnicismos como 'cefalera' o 'patología').
    2. Extrae la información para actualizar el formulario adjunto.
    3. Si el usuario habla en otro idioma, entiéndelo, pero respóndele en un español muy sencillo.
    
    ESTADO ACTUAL DEL FORMULARIO:
    {st.session_state.formulario}
    """
    
    class RespuestaSistema(BaseModel):
        respuesta_lectura_facil: str
        formulario_actualizado: FormularioCita
    
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": texto_usuario}
        ],
        response_format=RespuestaSistema
    )
    
    resultado = json.loads(response.choices.message.content)
    return resultado

def texto_a_voz(texto):
    """Transforma el texto de la IA en un audio hablado de alta calidad (TTS)"""
    response = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",  # Voz clara y profesional
        input=texto
    )
    # Guardamos temporalmente el archivo de audio
    audio_path = "respuesta.mp3"
    response.stream_to_file(audio_path)
    return audio_path

# 2. DISEÑO DE LA INTERFAZ DE USUARIO (UI)
st.title("🏥 Sistema de Tramitación Electrónica Inclusiva por Diseño")
st.subheader("Prototipo Inteligente: Petición de Cita Médica Accesible")

col1, col2 = st.columns([1, 1], gap="large")

# --- COLUMNA 1: EL FORMULARIO DE TRAMITACIÓN (SE RELLENA SOLO) ---
with col1:
    st.markdown("### 📋 Tu Formulario de Cita")
    st.caption("Esta sección muestra cómo el sistema digitaliza los datos de fondo sin que tengas que teclear.")
    
    # Campos visuales que se actualizan dinámicamente
    motivo = st.text_input("¿Qué le pasa al paciente? (Motivo)", value=st.session_state.formulario["motivo_consulta"], disabled=True)
    especialidad = st.selectbox("Especialidad asignada", ["", "Medicina General", "Pediatría", "Enfermería"], 
                                index=["", "Medicina General", "Pediatría", "Enfermería"].index(st.session_state.formulario["especialidad"]), disabled=True)
    horario = st.text_input("Preferencia de horario", value=st.session_state.formulario["preferencia_horario"], disabled=True)
    
    if st.session_state.formulario["datos_completos"]:
        st.success("✅ ¡Todo listo! Tu cita ha sido registrada con éxito.")
    else:
        st.info("⏳ Esperando completar los datos a través del asistente...")

# --- COLUMNA 2: EL ASISTENTE CON IA INCLUSIVA (CHAT Y VOZ) ---
with col2:
    st.markdown("### 💬 Asistente de Voz y Accesibilidad")
    
    # Mostrar el historial del chat de forma limpia
    for mensaje in st.session_state.historial_chat:
        with st.chat_message(mensaje["role"]):
            st.write(mensaje["content"])
            
    # Reproductor de audio automático para la última respuesta de la IA
    if st.session_state.audio_generado and os.path.exists(st.session_state.audio_generado):
        st.audio(st.session_state.audio_generado, format="audio/mp3", autoplay=True)
    
    st.markdown("---")
    st.markdown("**🎙️ ¿Prefieres hablar? Graba tu respuesta aquí:**")
    
    # Grabadora de voz en la interfaz web
    audio_bytes = st_audiorec()
    
    # Entrada de texto tradicional por si el usuario prefiere escribir
    entrada_texto = st.chat_input("Escribe aquí tu respuesta...")
    
    texto_a_procesar = ""
    
    # Escenario A: El usuario ha grabado un audio
    if audio_bytes is not None:
        with open("audio_usuario.wav", "wb") as f:
            f.write(audio_bytes)
        
        # Procesar audio con Whisper (Speech-to-Text de OpenAI)
        with open("audio_usuario.wav", "rb") as audio_file:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        texto_a_procesar = transcripcion.text
        # Limpiamos el audio grabado para evitar bucles de ejecución
        audio_bytes = None 
        
    # Escenario B: El usuario ha escrito texto
    elif entrada_texto:
        texto_a_procesar = entrada_texto

    # SI HAY NUEVA ENTRADA (Texto o Voz), PROCESAMOS:
    if texto_a_procesar:
        # 1. Añadir lo que dijo el usuario a la pantalla
        st.session_state.historial_chat.append({"role": "user", "content": texto_a_procesar})
        
        # 2. La IA lo analiza y actualiza el formulario
        with st.spinner("Pensando de forma inclusiva..."):
            resultado_ia = procesar_con_ia(texto_a_procesar)
        
        # 3. Guardar el nuevo estado del formulario y la respuesta
        st.session_state.formulario = resultado_ia["formulario_actualizado"]
        respuesta_texto = resultado_ia["respuesta_lectura_facil"]
        
        st.session_state.historial_chat.append({"role": "assistant", "content": respuesta_texto})
        
        # 4. Generar la voz de la IA (Text-to-Speech)
        archivo_voz = texto_a_voz(respuesta_texto)
        st.session_state.audio_generado = archivo_voz
        
        # Recargar la página para que se vean los cambios en el formulario y suene el audio
        st.rerun()
