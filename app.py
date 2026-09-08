import streamlit as st
import os
from openai import OpenAI
from pydantic import BaseModel, Field
import json

# Configuración de la página web
st.set_page_config(page_title="Cita Médica Inclusiva", layout="wide", page_icon="🏥")

# Inicializar la API de OpenAI desde los Secrets de Streamlit
API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "TU_OPENAI_API_KEY_AQUI"))
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
    """Envía la respuesta al modelo para actualizar el formulario y obtener respuesta multilingüe"""
    prompt_sistema = f"""
    Eres un asistente virtual inclusivo de un hospital. Tu meta es ayudar a pacientes a pedir una cita médica.
    
    REGLAS CRÍTICAS DE IDIOMA E INCLUSIÓN:
    1. DETECCIÓN DE IDIOMA: Detecta en qué idioma te está hablando el usuario (inglés, árabe, francés, etc.).
    2. RESPUESTA ADAPTADA: Responde SIEMPRE en el MISMO IDIOMA en el que te hable el usuario. Si te habla en inglés, responde en inglés; si te habla en árabe, en árabe.
    3. LECTURA FÁCIL: Sin importar el idioma que uses, aplica siempre las reglas de 'Lectura Fácil': frases muy cortas, palabras muy simples, tono amable y sin tecnicismos médicos difíciles.
    4. DIGITALIZACIÓN: Extrae los datos clave para actualizar el formulario (el formulario interno de fondo se guarda de manera normalizada).
    
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
        voice="shimmer",
        input=texto
    )
    audio_path = "respuesta.mp3"
    response.stream_to_file(audio_path)
    return audio_path

# 2. DISEÑO DE LA INTERFAZ DE USUARIO (UI)
st.title("🏥 Sistema de Tramitación Electrónica Inclusiva por Diseño")
st.subheader("Prototipo Inteligente: Petición de Cita Médica Accesible")

col1, col2 = st.columns(2, gap="large")

# --- COLUMNA 1: EL FORMULARIO DE TRAMITACIÓN ---
with col1:
    st.markdown("### 📋 Tu Formulario de Cita")
    st.caption("Esta sección muestra cómo el sistema digitaliza los datos de fondo sin que tengas que teclear.")
    
    st.text_input("¿Qué le pasa al paciente? (Motivo)", value=st.session_state.formulario["motivo_consulta"], disabled=True)
    
    lista_especialidades = ["", "Medicina General", "Pediatría", "Enfermería"]
    idx_esp = lista_especialidades.index(st.session_state.formulario["especialidad"]) if st.session_state.formulario["especialidad"] in lista_especialidades else 0
    st.selectbox("Especialidad asignada", lista_especialidades, index=idx_esp, disabled=True)
    
    st.text_input("Preferencia de horario", value=st.session_state.formulario["preferencia_horario"], disabled=True)
    
    if st.session_state.formulario["datos_completos"]:
        st.success("✅ ¡Todo listo! Tu cita ha sido registrada con éxito.")
    else:
        st.info("⏳ Esperando completar los datos a través del asistente...")

# --- COLUMNA 2: EL ASISTENTE CON IA INCLUSIVA ---
with col2:
    st.markdown("### 💬 Asistente de Voz y Accesibilidad")
    
    for mensaje in st.session_state.historial_chat:
        with st.chat_message(mensaje["role"]):
            st.write(mensaje["content"])
            
    if st.session_state.audio_generado and os.path.exists(st.session_state.audio_generado):
        st.audio(st.session_state.audio_generado, format="audio/mp3", autoplay=True)
    
    st.markdown("---")
    st.markdown("**🎙️ Usa el micrófono para hablar directamente con el asistente:**")
    
    # Grabador de audio nativo de Streamlit (Altamente accesible e integrado)
    archivo_audio = st.audio_input("Graba tu voz aquí")
    entrada_texto = st.chat_input("O escribe aquí tu respuesta si lo prefieres...")
    
    texto_a_procesar = ""
    
    if archivo_audio is not None:
        # Guardar temporalmente el audio capturado por el componente nativo
        with open("audio_usuario.wav", "wb") as f:
            f.write(archivo_audio.read())
        
        with open("audio_usuario.wav", "rb") as audio_file:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        texto_a_procesar = transcripcion.text
        
    elif entrada_texto:
        texto_a_procesar = entrada_texto

    if texto_a_procesar:
        st.session_state.historial_chat.append({"role": "user", "content": texto_a_procesar})
        
        with st.spinner("Procesando de forma inclusiva..."):
            resultado_ia = procesar_con_ia(texto_a_procesar)
        
        st.session_state.formulario = resultado_ia["formulario_actualizado"]
        respuesta_texto = resultado_ia["respuesta_lectura_facil"]
        
        st.session_state.historial_chat.append({"role": "assistant", "content": respuesta_texto})
        
        archivo_voz = texto_a_voz(respuesta_texto)
        st.session_state.audio_generado = archivo_voz
        
        st.rerun()
