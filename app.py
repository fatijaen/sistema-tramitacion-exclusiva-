import streamlit as st
import os
from openai import OpenAI
from pydantic import BaseModel, Field
import json
from streamlit_audiorec import st_audiorec  # Componente para grabar audio en web

# Configuración de la página web
st.set_page_config(page_title="Cita Médica Inclusiva", layout="wide", page_icon="🏥")

# Inicializar la API de OpenAI desde los Secrets de Streamlit o variable de entorno
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
    """Envía la respuesta al modelo para actualizar el formulario y obtener respuesta en Lectura Fácil.
    Se espera que el modelo responda con un JSON con dos claves:
      - respuesta_lectura_facil (string)
      - formulario_actualizado (objeto con las claves del formulario)
    Esta función es robusta frente a distintas formas de respuesta del modelo.
    """
    prompt_sistema = f"""
    Eres un asistente virtual inclusivo de un hospital. Tu meta es ayudar a pacientes (mayores, extranjeros o con dificultades) a pedir cita.

    REGLAS:
    1. Responde SIEMPRE en español con LECTURA FÁCIL (frases cortas, claras, sin tecnicismos como 'cefalera' o 'patología').
    2. Extrae la información para actualizar el formulario adjunto.
    3. Si el usuario habla en otro idioma, entiéndelo, pero respóndele en un español muy sencillo.

    ESTADO ACTUAL DEL FORMULARIO:
    {st.session_state.formulario}

    INSTRUCCIONES DE SALIDA:
    Responde SOLO con un JSON válido con las claves: "respuesta_lectura_facil" y "formulario_actualizado". Ejemplo:
    {{"respuesta_lectura_facil": "Texto simple...", "formulario_actualizado": {{"motivo_consulta": "...", "especialidad": "Medicina General", "preferencia_horario": "Mañana", "datos_completos": true}}}}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=1000,
            temperature=0.2,
        )

        # Extraer el contenido de la primera elección
        content = None
        if hasattr(response, "choices") and len(response.choices) > 0:
            choice0 = response.choices[0]
            if isinstance(choice0, dict):
                content = choice0.get("message", {}).get("content") or choice0.get("text")
            else:
                # intentamos acceder por atributos
                message = getattr(choice0, "message", None)
                if message:
                    content = getattr(message, "content", None)
                if not content:
                    content = getattr(choice0, "text", None)

        if not content:
            raise ValueError("No se recibió contenido del modelo.")

        # Intentar parsear JSON directo
        try:
            resultado = json.loads(content)
        except Exception:
            # Extraer primer objeto JSON en el texto
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    resultado = json.loads(content[start:end+1])
                except Exception:
                    raise ValueError("No se pudo parsear JSON de la respuesta del modelo.")
            else:
                raise ValueError("La respuesta del modelo no contiene JSON.")

        # Validar estructura mínima
        if "respuesta_lectura_facil" not in resultado or "formulario_actualizado" not in resultado:
            raise ValueError("La respuesta del modelo no contiene las claves esperadas.")

        return resultado

    except Exception as e:
        st.error(f"Error al comunicarse con el modelo de IA: {e}")
        return {
            "respuesta_lectura_facil": "Lo siento, he tenido un problema y no puedo procesar tu mensaje ahora. Intenta de nuevo más tarde.",
            "formulario_actualizado": st.session_state.formulario
        }


def texto_a_voz(texto):
    """Transforma el texto de la IA en un audio hablado de alta calidad (TTS)."""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="shimmer",
            input=texto
        )
        audio_path = "respuesta.mp3"
        if hasattr(response, "stream_to_file"):
            response.stream_to_file(audio_path)
        else:
            content = getattr(response, "content", None) or getattr(response, "audio", None)
            if content:
                with open(audio_path, "wb") as f:
                    f.write(content)
            else:
                raise ValueError("La respuesta de TTS no contiene audio.")
        return audio_path
    except Exception as e:
        st.error(f"Error al generar la voz: {e}")
        return None

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

    opciones_especialidad = ["", "Medicina General", "Pediatría", "Enfermería"]
    try:
        index_actual = opciones_especialidad.index(st.session_state.formulario.get("especialidad", ""))
    except ValueError:
        index_actual = 0

    especialidad = st.selectbox(
        "Especialidad asignada",
        opciones_especialidad,
        index=index_actual,
        disabled=True,
    )

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
        try:
            with open("audio_usuario.wav", "wb") as f:
                f.write(audio_bytes)

            # Procesar audio con Whisper (Speech-to-Text de OpenAI)
            with open("audio_usuario.wav", "rb") as audio_file:
                transcripcion = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            texto_a_procesar = getattr(transcripcion, "text", None) or (transcripcion.get("text") if isinstance(transcripcion, dict) else None) or ""
        except Exception as e:
            st.error(f"Error al transcribir el audio: {e}")
            texto_a_procesar = ""

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
        formulario_actualizado = resultado_ia.get("formulario_actualizado") if isinstance(resultado_ia, dict) else None
        if formulario_actualizado is None:
            formulario_actualizado = st.session_state.formulario

        st.session_state.formulario = formulario_actualizado
        respuesta_texto = resultado_ia.get("respuesta_lectura_facil", "Lo siento, no entendí. ¿Puedes repetir?")

        st.session_state.historial_chat.append({"role": "assistant", "content": respuesta_texto})

        # 4. Generar la voz de la IA (Text-to-Speech)
        archivo_voz = texto_a_voz(respuesta_texto)
        st.session_state.audio_generado = archivo_voz

        # Recargar la página para que se vean los cambios en el formulario y suene el audio
        st.rerun()
