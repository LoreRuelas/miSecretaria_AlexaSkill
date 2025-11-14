# handlers.py
import logging
import re
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_model import Response
from datetime import datetime

from data_manager import (
    register_user,
    find_user_by_name_or_phone,
    normalize_name,
    get_doctor_info,
    get_available_slots,
    save_appointment,
    user_has_appointment,
    get_user_appointment,
    cancel_appointment,
    move_appointment,
    day_name_to_next_iso
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ASK_REGISTER_INSTRUCTIONS = (
    'Por favor dime: "mi nombre es [tu nombre] y mi teléfono es [tu teléfono]". '
    'Por ejemplo: "mi nombre es Diego y mi teléfono es 5551234567".'
)
REPROMPT_GENERIC = "¿En qué más puedo ayudarte?"

# -----------------------
# Util: parseo de horas habladas
# -----------------------
NUMS = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "dieciseís": 16, "dieciseis": 16,
    "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintidos": 22, "veintidós": 22, "veintitrés": 23, "veintitres": 23
}

def parse_hour_from_text(text: str):
    """
    Intenta parsear texto hablado a 'HH:MM' (24h).
    Acepta: '15:00', '3 pm', 'tres', 'tres dos ceros', 'tres cero cero', 'quince', '15'
    Retorna 'HH:MM' o None
    """
    if not text:
        return None
    t = text.strip().lower()
    # si viene en formato ISO/hora
    m = re.search(r'(\d{1,2}):(\d{2})', t)
    if m:
        h = int(m.group(1))
        mnt = int(m.group(2))
        return f"{h:02d}:{mnt:02d}"
    # detectar "pm" o "a.m."
    pm = "pm" in t or "p.m." in t or "p m" in t
    am = "am" in t or "a.m." in t or "a m" in t
    # extraer números en palabras
    words = re.findall(r"[a-záéíóúñ]+|\d+", t)
    nums = []
    for w in words:
        if w.isdigit():
            nums.append(int(w))
        else:
            w_clean = w.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n")
            if w_clean in NUMS:
                nums.append(NUMS[w_clean])
    if len(nums) >= 1:
        hour = nums[0]
        minute = 0
        if len(nums) >= 2:
            # caso 'tres dos' -> 3:02? no; tratamos 'tres dos ceros' -> 3:00 => si segundo número == 0 -> 00
            # Normalizamos: si segundo es 0, minute 00; si >=10 and <60 use como minutos
            s = nums[1]
            if s == 0 or s == 00:
                minute = 0
            elif s < 10:
                # si usuario dijo 'tres cero cero' -> nums [3,0,0]
                # si usuario dijo 'tres dos' es ambiguo -> interpretamos como minutos 02
                minute = s
            else:
                # si s >=10 asume minutos
                minute = s
        # ajustar por pm/am si aplica
        if pm and 1 <= hour <= 11:
            hour += 12
        if am and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    return None

def extract_day_and_time_from_text(text: str):
    """
    Extrae un día (palabra) y una hora (texto) de un texto libre como:
    'martes a las tres dos ceros' -> ('martes', 'tres dos ceros')
    Retorna (day_word_or_None, time_text_or_None)
    """
    if not text:
        return (None, None)
    t = text.lower()
    # buscar día
    day_word = None
    for d in DIAS_ENG_TO_ESP.values():
        if d in t:
            day_word = d
            break
    # si no encontró en valores directos, buscar español alternativo sin acentos
    for k in DIAS_ESP_TO_INDEX.keys():
        if k in t:
            day_word = k
            break
    # time: buscar patrón "a las ..." o "a la(s) ..."
    time_text = None
    m = re.search(r'(?:a las|a la|a las las|a lasl)\s+(.+)', t)
    if m:
        time_text = m.group(1).strip()
    else:
        # intentar extraer la parte que contiene números/palabras tras el día
        if day_word:
            parts = t.split(day_word, 1)
            if len(parts) > 1:
                time_text = parts[1].strip()
                # quitar 'a las' si quedó
                time_text = re.sub(r'^(a las|a la|:)\s*', '', time_text)
    return (day_word, time_text)

# -----------------------
# Handlers
# -----------------------
class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        if not session.get("user_key"):
            session["awaiting_registration"] = True
            speak = (
                "Hola, soy tu secretaria personal. Antes de empezar, por favor registra tu nombre y teléfono. "
                + ASK_REGISTER_INSTRUCTIONS
            )
            return handler_input.response_builder.speak(speak).ask(speak).response
        nombre = session.get("user_nombre")
        speak = f"Hola {nombre}. ¿En qué puedo ayudarte?"
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

class RegistrarUsuarioIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("RegistrarUsuarioIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        nombre = slots.get("nombre").value if slots.get("nombre") else None
        telefono = slots.get("telefono").value if slots.get("telefono") else None
        # si usuario dijo solo nombre separado (ej: "mi nombre es diego"), slot telefono vendrá vacío
        if not nombre:
            session["awaiting_registration"] = True
            speak = "No identifiqué tu nombre. " + ASK_REGISTER_INSTRUCTIONS
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response
        if not telefono:
            session["awaiting_registration"] = True
            speak = "No identifiqué tu teléfono. " + ASK_REGISTER_INSTRUCTIONS
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response
        user_key = register_user(nombre, telefono)
        session["user_key"] = user_key
        session["user_nombre"] = nombre
        session["user_telefono"] = telefono
        session.pop("awaiting_registration", None)
        speak = (
            f"Perfecto {nombre}. Te he registrado. "
            "Puedo ayudarte a agendar, mover o cancelar una cita, o darte información de los doctores y la clínica. "
            "¿Qué deseas hacer?"
        )
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

class AgendarCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AgendarCitaIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        user_key = session.get("user_key")
        if not user_key:
            session["awaiting_registration"] = True
            speak = "Antes de agendar necesito registrar tu nombre y teléfono. " + ASK_REGISTER_INSTRUCTIONS
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response
        # extraer slots
        doctor_raw = None
        if slots.get("doctor") and slots.get("doctor").value:
            doctor_raw = slots.get("doctor").value
        fecha_slot = slots.get("fecha").value if slots.get("fecha") else None
        hora_slot = slots.get("hora").value if slots.get("hora") else None
        # si usuario está en estado "esperando fecha/hora" tras confirmar doctor previamente
        if session.get("pending_action") == "awaiting_datetime":
            # intentar extraer desde lo que llegue en slots o desde el texto libre si el slot 'fecha' tiene 'martes a las tres...'
            # primero checar si fecha_slot tiene palabra día (p.ej 'martes')
            day = None
            time_text = None
            if fecha_slot:
                # Alexa a veces coloca 'martes' en fecha_slot as text; si es ISO (YYYY-MM-DD) lo tomamos directo
                if re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_slot):
                    fecha_iso = fecha_slot
                else:
                    # fecha_slot puede ser 'martes' o 'martes a las tres'
                    d, tt = extract_day_and_time_from_text(fecha_slot)
                    if d:
                        day = d
                        time_text = tt
                    else:
                        # si fecha_slot no contiene día pero contiene full date text, fallback to None
                        fecha_iso = None
                # si fecha_slot no dio fecha_iso, usar day detection below
            else:
                fecha_iso = None
            # si hora_slot presente, preferirlo
            if hora_slot:
                hora_parsed = parse_hour_from_text(hora_slot)
            else:
                hora_parsed = None
            # si time_text del extract
            if not hora_parsed and time_text:
                hora_parsed = parse_hour_from_text(time_text)
            # si no tenemos fecha_iso pero tenemos day palabra -> convertir a iso
            if not fecha_slot and session.get("pending_doctor") and session.get("pending_fecha_text"):
                # caso: previously asked date and user responded only time; but here we handle explicit day
                pass
            if day:
                fecha_iso = day_name_to_next_iso(day)
            # si aún no hay hora ni fecha intentar extraer de texto libre (Alexa puede poner todo en 'hora' slot)
            if not fecha_iso and not hora_parsed and (hora_slot and isinstance(hora_slot, str)):
                # intentar parse: 'martes a las tres dos ceros'
                d, tt = extract_day_and_time_from_text(hora_slot)
                if d:
                    fecha_iso = day_name_to_next_iso(d)
                if tt:
                    hora_parsed = parse_hour_from_text(tt)
            # si ya tenemos fecha_iso e hora_parsed -> confirmar guardado
            if fecha_iso and hora_parsed:
                # validar disponibilidad
                doc_key = session.get("pending_doctor")
                if not doc_key:
                    speak = "No tengo el doctor asignado. Por favor diga con qué doctor desea la cita."
                    session.pop("pending_action", None)
                    return handler_input.response_builder.speak(speak).ask(speak).response
                disponibles = get_available_slots(doc_key, fecha_iso)
                if hora_parsed not in disponibles:
                    speak = f"La hora {hora_parsed} no está disponible para ese doctor el {fecha_iso}. Opciones: {', '.join(disponibles[:4])}."
                    return handler_input.response_builder.speak(speak).ask("¿Desea otra hora?").response
                # preparar confirmación
                session["pending_action"] = "confirm_agendar"
                session["pending_cita"] = {"doctor": doc_key, "fecha": fecha_iso, "hora": hora_parsed}
                doc = get_doctor_info(doc_key)
                speak = f"¿Confirmas agendar con {doc['nombre']} el {fecha_iso} a las {hora_parsed}?"
                return handler_input.response_builder.speak(speak).ask(speak).response
            # si falta algo, pedir lo que falta
            if not fecha_iso and not hora_parsed:
                speak = "No entendí la fecha ni la hora. Por favor indica el día (por ejemplo martes) y la hora (por ejemplo 15:00 o tres pm)."
                return handler_input.response_builder.speak(speak).ask(speak).response
            if not fecha_iso:
                speak = "¿Qué día deseas para la cita?"
                return handler_input.response_builder.speak(speak).ask(speak).response
            if not hora_parsed:
                speak = "¿A qué hora deseas la cita?"
                return handler_input.response_builder.speak(speak).ask(speak).response
        # flujo normal: usuario puede entregar doctor/fecha/hora en un solo utterance
        if not doctor_raw:
            speak = "¿Con cuál doctor desea agendar? Tenemos disponibles: Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response
        doctor = get_doctor_info(doctor_raw)
        if not doctor:
            speak = "No encontré ese doctor. Los disponibles son Ramírez, Gómez y Hernández. ¿Con cuál desea?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        # si usuario entregó fecha literal en ISO (Alexa puede hacerlo) y hora en slot
        fecha_iso = None
        hora_parsed = None
        if fecha_slot and re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_slot):
            fecha_iso = fecha_slot
        elif fecha_slot:
            # intenta extraer 'martes' etc
            d, tt = extract_day_and_time_from_text(fecha_slot)
            if d:
                fecha_iso = day_name_to_next_iso(d)
                if tt:
                    hora_parsed = parse_hour_from_text(tt)
        if hora_slot:
            hora_parsed = parse_hour_from_text(hora_slot) or hora_parsed
        # si no hay fecha/hora -> guardar pending doctor y preguntar
        if not fecha_iso and not hora_parsed:
            # pedir fecha/hora
            session["pending_doctor"] = doctor["key"]
            session["pending_action"] = "awaiting_datetime"
            speak = f"{doctor['nombre']} es especialista en {doctor['especialidad']}. Atiende {', '.join(doctor['dias'])} de {doctor['inicio']}:00 a {doctor['fin']}:00. ¿Qué día y hora prefieres?"
            return handler_input.response_builder.speak(speak).ask("Por favor di el día y la hora.").response
        # si tenemos fecha_iso pero no hora -> listar franjas
        if fecha_iso and not hora_parsed:
            disponibles = get_available_slots(doctor["key"], fecha_iso)
            if not disponibles:
                speak = f"No hay franjas disponibles para {doctor['nombre']} el {fecha_iso}."
                return handler_input.response_builder.speak(speak).ask("¿Desea otra fecha?").response
            opciones = ", ".join(disponibles[:4])
            session["pending_doctor"] = doctor["key"]
            session["pending_fecha"] = fecha_iso
            session["pending_action"] = "awaiting_time"
            speak = f"En {fecha_iso} las horas disponibles son: {opciones}. ¿Qué hora prefieres?"
            return handler_input.response_builder.speak(speak).ask("¿Qué hora prefieres?").response
        # si tenemos ambos -> validar y pedir confirmación
        if fecha_iso and hora_parsed:
            disponibles = get_available_slots(doctor["key"], fecha_iso)
            if hora_parsed not in disponibles:
                speak = f"La hora {hora_parsed} no está disponible para {doctor['nombre']} el {fecha_iso}. Opciones: {', '.join(disponibles[:4])}."
                return handler_input.response_builder.speak(speak).ask("¿Desea elegir otra hora?").response
            session["pending_action"] = "confirm_agendar"
            session["pending_cita"] = {"doctor": doctor["key"], "fecha": fecha_iso, "hora": hora_parsed}
            speak = f"¿Confirma que desea agendar cita con {doctor['nombre']} el {fecha_iso} a las {hora_parsed}?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        # fallback
        speak = "No entendí la información de la cita. Por favor diga: agendar cita con el doctor, fecha y hora."
        return handler_input.response_builder.speak(speak).ask(speak).response

class ConsultarCitasIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConsultarCitasIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        user_key = session.get("user_key")
        if not user_key:
            session["awaiting_registration"] = True
            speak = "No te encuentro registrado. " + ASK_REGISTER_INSTRUCTIONS
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response
        cita = get_user_appointment(user_key)
        if not cita:
            speak = "No tienes citas activas. ¿Deseas agendar una?"
            return handler_input.response_builder.speak(speak).ask("¿Deseas agendar?").response
        doc = get_doctor_info(cita["doctor"])
        speak = f"Tienes una cita con {doc['nombre']} el {cita['fecha']} a las {cita['hora']}. ¿Deseas moverla o cancelarla?"
        return handler_input.response_builder.speak(speak).ask("¿Mover o cancelar?").response

class CancelarCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("CancelarCitaIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        user_key = session.get("user_key")
        if not user_key:
            session["awaiting_registration"] = True
            speak = "No estás registrado. " + ASK_REGISTER_INSTRUCTIONS
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response
        cita = get_user_appointment(user_key)
        if not cita:
            speak = "No tienes ninguna cita para cancelar."
            return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
        doc = get_doctor_info(cita["doctor"])
        session["pending_action"] = "confirm_cancel"
        speak = f"¿Confirmas que deseas cancelar tu cita con {doc['nombre']} el {cita['fecha']} a las {cita['hora']}?"
        return handler_input.response_builder.speak(speak).ask(speak).response

class MoverCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("MoverCitaIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        user_key = session.get("user_key")
        if not user_key:
            session["awaiting_registration"] = True
            speak = "No estás registrado. " + ASK_REGISTER_INSTRUCTIONS
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response
        cita = get_user_appointment(user_key)
        if not cita:
            speak = "No tienes una cita activa para mover. ¿Deseas agendar una nueva?"
            return handler_input.response_builder.speak(speak).ask("¿Deseas agendar?").response
        # si el usuario da nueva fecha/hora en el mismo intent, manejarlo (slots 'nueva_fecha','nueva_hora')
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        nueva_fecha = slots.get("nueva_fecha").value if slots.get("nueva_fecha") else None
        nueva_hora = slots.get("nueva_hora").value if slots.get("nueva_hora") else None
        doctor_key = cita["doctor"]
        if not nueva_fecha:
            session["pending_action"] = "move_ask_date"
            speak = "¿Qué fecha deseas para la nueva cita?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        if nueva_fecha and not nueva_hora:
            disponibles = get_available_slots(doctor_key, nueva_fecha)
            if not disponibles:
                speak = f"No hay franjas disponibles para esa fecha. ¿Deseas otra fecha?"
                return handler_input.response_builder.speak(speak).ask("¿Otra fecha?").response
            opciones = ", ".join(disponibles[:4])
            session["pending_action"] = "move_ask_time"
            session["pending_new_date"] = nueva_fecha
            speak = f"Las horas disponibles para {nueva_fecha} son: {opciones}. ¿Qué hora prefieres?"
            return handler_input.response_builder.speak(speak).ask("¿Qué hora prefieres?").response
        if nueva_fecha and nueva_hora:
            disponibles = get_available_slots(doctor_key, nueva_fecha)
            if nueva_hora not in disponibles:
                speak = f"La hora {nueva_hora} no está disponible. Opciones: {', '.join(disponibles[:4])}."
                return handler_input.response_builder.speak(speak).ask("¿Otra hora?").response
            session["pending_action"] = "confirm_move"
            session["pending_new_cita"] = {"fecha": nueva_fecha, "hora": nueva_hora}
            doc = get_doctor_info(doctor_key)
            speak = f"Confirma mover tu cita a {nueva_fecha} a las {nueva_hora} con {doc['nombre']}?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        speak = "No entendí la solicitud para mover la cita."
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

class InfoDoctorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("InfoDoctorIntent")(handler_input)
    def handle(self, handler_input):
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        doctor_raw = slots.get("doctor").value if slots.get("doctor") else None
        if not doctor_raw:
            speak = "¿Sobre qué doctor deseas información? Tenemos: Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response
        doc = get_doctor_info(doctor_raw)
        if not doc:
            speak = f"No encontré al doctor {doctor_raw}. ¿Deseas información de Ramírez, Gómez o Hernández?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        dias = ", ".join(doc["dias"])
        speak = f"{doc['nombre']} es especialista en {doc['especialidad']}. Atiende los días {dias} de {doc['inicio']}:00 a {doc['fin']}:00. ¿Deseas agendar con este doctor?"
        # guardar doctor seleccionado por si responde "sí"
        session = handler_input.attributes_manager.session_attributes
        session["pending_doctor"] = doc["key"]
        session["pending_action"] = "awaiting_datetime"
        return handler_input.response_builder.speak(speak).ask("¿Qué día y hora prefieres?").response

class DisponibilidadDoctorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("DisponibilidadDoctorIntent")(handler_input)
    def handle(self, handler_input):
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        doctor_raw = slots.get("doctor").value if slots.get("doctor") else None
        fecha = slots.get("fecha").value if slots.get("fecha") else None
        if not doctor_raw:
            speak = "¿De qué doctor necesitas la disponibilidad?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        doc = get_doctor_info(doctor_raw)
        if not doc:
            speak = "No encontré ese doctor. Tenemos: Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response
        if not fecha:
            speak = "¿Para qué fecha necesitas la disponibilidad? Por ejemplo: 2025-11-20."
            session = handler_input.attributes_manager.session_attributes
            session["pending_doctor"] = doc["key"]
            session["pending_action"] = "awaiting_date_for_availability"
            return handler_input.response_builder.speak(speak).ask(speak).response
        # si fecha es palabra 'martes' convertir
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
            fecha_iso = day_name_to_next_iso(fecha)
        else:
            fecha_iso = fecha
        disponibles = get_available_slots(doc["key"], fecha_iso)
        if not disponibles:
            speak = f"No hay horarios disponibles para {doc['nombre']} el {fecha_iso}."
            return handler_input.response_builder.speak(speak).ask("¿Deseas otra fecha?").response
        opciones = ", ".join(disponibles[:6])
        speak = f"Las horas disponibles para {doc['nombre']} el {fecha_iso} son: {opciones}. ¿Quieres agendar alguna?"
        return handler_input.response_builder.speak(speak).ask("¿Deseas agendar alguna?").response

class YesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        pending = session.get("pending_action")
        user_key = session.get("user_key")
        # respuesta a confirmación de agendado
        if pending == "confirm_agendar":
            pending_cita = session.get("pending_cita")
            if not pending_cita or not user_key:
                speak = "No tengo la información completa para agendar."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
            success = save_appointment(user_key, pending_cita["doctor"], pending_cita["fecha"], pending_cita["hora"])
            session.pop("pending_cita", None)
            session.pop("pending_action", None)
            if success:
                doc = get_doctor_info(pending_cita["doctor"])
                speak = f"Listo — su cita con {doc['nombre']} quedó agendada para el {pending_cita['fecha']} a las {pending_cita['hora']}."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
            speak = "Lo siento, esa franja ya no está disponible."
            return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
        # usuario confirmó doctor e inició flujo -> ahora pedir fecha/hora
        if pending in (None, "awaiting_datetime", "awaiting_time"):
            # si hay doctor pendiente, pedir fecha/hora
            doc_key = session.get("pending_doctor")
            if not doc_key:
                return handler_input.response_builder.speak("¿Qué deseas hacer?").ask(REPROMPT_GENERIC).response
            session["pending_action"] = "awaiting_datetime"
            speak = "Perfecto. ¿Qué día y a qué hora deseas la cita?"
            return handler_input.response_builder.speak(speak).ask(speak).response
        # confirm cancel
        if pending == "confirm_cancel":
            if not user_key:
                return handler_input.response_builder.speak("No estás registrado.").ask(ASK_REGISTER_INSTRUCTIONS).response
            success = cancel_appointment(user_key)
            session.pop("pending_action", None)
            if success:
                return handler_input.response_builder.speak("Su cita ha sido cancelada correctamente. ¿Deseas algo más?").ask(REPROMPT_GENERIC).response
            return handler_input.response_builder.speak("No encontré una cita para cancelar.").ask(REPROMPT_GENERIC).response
        # confirm move
        if pending == "confirm_move":
            new = session.get("pending_new_cita")
            if not new or not user_key:
                return handler_input.response_builder.speak("No hay movimiento pendiente.").ask(REPROMPT_GENERIC).response
            success = move_appointment(user_key, new["fecha"], new["hora"])
            session.pop("pending_action", None)
            session.pop("pending_new_cita", None)
            if success:
                return handler_input.response_builder.speak(f"Su cita fue movida a {new['fecha']} a las {new['hora']}. ¿Desea algo más?").ask(REPROMPT_GENERIC).response
            return handler_input.response_builder.speak("No fue posible mover la cita a esa franja.").ask(REPROMPT_GENERIC).response
        # por defecto
        return handler_input.response_builder.speak("De acuerdo. ¿Necesitas algo más?").ask(REPROMPT_GENERIC).response

class NoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        session.pop("pending_action", None)
        session.pop("pending_cita", None)
        session.pop("pending_new_cita", None)
        return handler_input.response_builder.speak("De acuerdo, no se realizó ningún cambio. ¿Necesitas algo más?").ask(REPROMPT_GENERIC).response

class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)
    def handle(self, handler_input):
        speak = "Disculpa, no entendí esa solicitud. Puedes decir: agendar cita, consultar mis citas, cancelar o mover una cita."
        return handler_input.response_builder.speak(speak).ask(speak).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)
    def handle(self, handler_input):
        return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak = "Hubo un problema procesando tu solicitud. Por favor intenta de nuevo."
        return handler_input.response_builder.speak(speak).ask(speak).response

# SkillBuilder export (used by lambda_function)
sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(RegistrarUsuarioIntentHandler())
sb.add_request_handler(AgendarCitaIntentHandler())
sb.add_request_handler(ConsultarCitasIntentHandler())
sb.add_request_handler(CancelarCitaIntentHandler())
sb.add_request_handler(MoverCitaIntentHandler())
sb.add_request_handler(InfoDoctorIntentHandler())
sb.add_request_handler(DisponibilidadDoctorIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())
