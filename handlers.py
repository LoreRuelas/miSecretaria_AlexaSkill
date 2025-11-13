# handlers.py
import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_model import Response

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
    move_appointment
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Helper prompts
WELCOME_PROMPT = (
    "Hola, soy tu secretaria personal. Puedo ayudarte a agendar, mover o cancelar una cita, "
    "o darte información de los doctores y la clínica. ¿Con qué te gustaría empezar?"
)

ASK_REGISTER_INSTRUCTIONS = (
    'Por favor dime: "mi nombre es [tu nombre] y mi teléfono es [tu teléfono]" '
    '—por ejemplo: "mi nombre es Diego y mi teléfono es 5551234567".'
)

REPROMPT_GENERIC = "¿En qué más puedo ayudarte?"

# --- Launch ---
class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        # si no hay usuario registrado en la sesión, pedir registro
        if not session_attr.get("user_key"):
            speak = WELCOME_PROMPT + " Antes de empezar, por favor registra tu nombre y teléfono. " + ASK_REGISTER_INSTRUCTIONS
            session_attr["awaiting_registration"] = True
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response

        speak = WELCOME_PROMPT
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

# --- Registrar Usuario ---
class RegistrarUsuarioIntentHandler(AbstractRequestHandler):
    """
    Espera que el usuario diga: 'mi nombre es X y mi teléfono es Y'
    Slots esperados: nombre (o slot que capture texto libre), telefono (AMAZON.PhoneNumber o texto)
    """
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("RegistrarUsuarioIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}

        nombre_slot = None
        telefono_slot = None
        # intentar múltiples nombres de slot por compatibilidad
        if slots.get("nombre"):
            nombre_slot = slots.get("nombre").value
        elif slots.get("name"):
            nombre_slot = slots.get("name").value

        if slots.get("telefono"):
            telefono_slot = slots.get("telefono").value

        if not nombre_slot:
            speak = "No identifiqué tu nombre. " + ASK_REGISTER_INSTRUCTIONS
            session_attr["awaiting_registration"] = True
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response

        user_key = register_user(nombre_slot, telefono_slot)
        session_attr["user_key"] = user_key
        session_attr["user_nombre"] = nombre_slot
        session_attr["user_telefono"] = telefono_slot
        session_attr.pop("awaiting_registration", None)

        speak = f"Perfecto {nombre_slot}. Te he registrado. {REPROMPT_GENERIC}"
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

# --- Agendar cita ---
class AgendarCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AgendarCitaIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}

        # Verificar usuario registrado en sesión
        user_key = session_attr.get("user_key")
        if not user_key:
            # pedir registro
            session_attr["awaiting_registration"] = True
            speak = (
                "Antes de agendar necesito registrar tu nombre y teléfono. "
                + ASK_REGISTER_INSTRUCTIONS
            )
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response

        # Extraer slots
        doctor_raw = slots.get("doctor").value if slots.get("doctor") else None
        fecha = slots.get("fecha").value if slots.get("fecha") else None
        hora = slots.get("hora").value if slots.get("hora") else None

        if not doctor_raw:
            speak = "¿Con cuál doctor desea agendar? Tenemos disponibles: Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response

        doctor_key = normalize_name(doctor_raw)
        doctor_info = get_doctor_info(doctor_key)
        if not doctor_info:
            speak = f"Lo siento, no encontré al doctor {doctor_raw}. Los doctores disponibles son Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask("¿Desea intentar con otro doctor?").response

        # Si ya tiene cita activa -> ofrecer mover o cancelar
        if user_has_appointment(user_key):
            cita = get_user_appointment(user_key)
            doc_nombre = get_doctor_info(cita["doctor"])["nombre"]
            speak = (
                f"Usted ya tiene una cita activa con {doc_nombre} el {cita['fecha']} a las {cita['hora']}. "
                "¿Desea moverla o cancelarla antes de agendar otra?"
            )
            session_attr["pending_action"] = "user_has_appointment"
            return handler_input.response_builder.speak(speak).ask("¿Desea moverla o cancelarla?").response

        # Si falta fecha/hora -> mostrar disponibilidad para la fecha si falta
        if not fecha:
            speak = f"¿Qué día desea? Por favor indique la fecha (por ejemplo 2025-11-20)."
            session_attr["pending_doctor"] = doctor_key
            return handler_input.response_builder.speak(speak).ask(speak).response

        # Si fecha dada pero no hora -> mostrar franjas
        if fecha and not hora:
            disponibles = get_available_slots(doctor_key, fecha)
            if not disponibles:
                speak = f"Lo siento, no hay franjas disponibles para {doctor_info['nombre']} el {fecha}."
                return handler_input.response_builder.speak(speak).ask("¿Desea otra fecha?").response
            # listar primeras 4 opciones
            opciones = ", ".join(disponibles[:4])
            speak = f"En {fecha} las horas disponibles son: {opciones}. ¿Qué hora prefiere?"
            session_attr["pending_doctor"] = doctor_key
            session_attr["pending_fecha"] = fecha
            return handler_input.response_builder.speak(speak).ask("¿Qué hora prefiere?").response

        # Si tenemos doctor, fecha y hora -> validar disponibilidad y pedir confirmación
        if fecha and hora:
            disponibles = get_available_slots(doctor_key, fecha)
            if hora not in disponibles:
                speak = f"La hora {hora} no está disponible para {doctor_info['nombre']} el {fecha}. Las opciones son: {', '.join(disponibles[:4])}."
                session_attr["pending_doctor"] = doctor_key
                session_attr["pending_fecha"] = fecha
                return handler_input.response_builder.speak(speak).ask("¿Desea elegir otra hora?").response

            # preparar pending cita y pedir confirmación
            session_attr["pending_action"] = "confirm_agendar"
            session_attr["pending_cita"] = {"doctor": doctor_key, "fecha": fecha, "hora": hora}
            speak = f"¿Confirma que desea agendar cita con {doctor_info['nombre']} el {fecha} a las {hora}?"
            return handler_input.response_builder.speak(speak).ask(speak).response

        speak = "No entendí la información de la cita. Por favor diga: quiero agendar una cita con el doctor, fecha y hora."
        return handler_input.response_builder.speak(speak).ask(speak).response

# --- Consultar citas ---
class ConsultarCitasIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("ConsultarCitasIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        user_key = session_attr.get("user_key")
        if not user_key:
            speak = "No te encuentro registrado. " + ASK_REGISTER_INSTRUCTIONS
            session_attr["awaiting_registration"] = True
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response

        cita = get_user_appointment(user_key)
        if not cita:
            speak = "No tienes citas activas actualmente. ¿Deseas agendar una?"
            return handler_input.response_builder.speak(speak).ask("¿Deseas agendar una cita?").response

        doc = get_doctor_info(cita["doctor"])
        speak = f"Tienes una cita con {doc['nombre']} el {cita['fecha']} a las {cita['hora']}. ¿Deseas cambiarla o cancelarla?"
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

# --- Cancelar cita ---
class CancelarCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("CancelarCitaIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        user_key = session_attr.get("user_key")
        if not user_key:
            speak = "No estás registrado. " + ASK_REGISTER_INSTRUCTIONS
            session_attr["awaiting_registration"] = True
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response

        cita = get_user_appointment(user_key)
        if not cita:
            speak = "No tienes ninguna cita para cancelar."
            return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

        doc = get_doctor_info(cita["doctor"])
        session_attr["pending_action"] = "confirm_cancel"
        speak = f"¿Confirmas que deseas cancelar tu cita con {doc['nombre']} el {cita['fecha']} a las {cita['hora']}?"
        return handler_input.response_builder.speak(speak).ask(speak).response

# --- Mover cita ---
class MoverCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("MoverCitaIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        user_key = session_attr.get("user_key")
        if not user_key:
            speak = "No estás registrado. " + ASK_REGISTER_INSTRUCTIONS
            session_attr["awaiting_registration"] = True
            return handler_input.response_builder.speak(speak).ask(ASK_REGISTER_INSTRUCTIONS).response

        cita = get_user_appointment(user_key)
        if not cita:
            speak = "No tienes una cita activa para mover. ¿Deseas agendar una nueva?"
            return handler_input.response_builder.speak(speak).ask("¿Deseas agendar una cita?").response

        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        nueva_fecha = slots.get("nueva_fecha").value if slots.get("nueva_fecha") else None
        nueva_hora = slots.get("nueva_hora").value if slots.get("nueva_hora") else None

        doctor_key = cita["doctor"]
        if not nueva_fecha:
            # preguntar fecha
            session_attr["pending_action"] = "move_ask_date"
            speak = "¿Qué fecha desea para la nueva cita?"
            return handler_input.response_builder.speak(speak).ask(speak).response

        # si fecha dada pero no hora -> proponer franjas
        if nueva_fecha and not nueva_hora:
            disponibles = get_available_slots(doctor_key, nueva_fecha)
            if not disponibles:
                speak = f"No hay franjas disponibles para esa fecha. ¿Deseas otra fecha?"
                return handler_input.response_builder.speak(speak).ask("¿Deseas otra fecha?").response
            opciones = ", ".join(disponibles[:4])
            session_attr["pending_action"] = "move_ask_time"
            session_attr["pending_new_date"] = nueva_fecha
            speak = f"Para {nueva_fecha} las horas disponibles son: {opciones}. ¿Qué hora prefieres?"
            return handler_input.response_builder.speak(speak).ask("¿Qué hora prefieres?").response

        # Si tenemos fecha y hora -> pedir confirmación para mover
        if nueva_fecha and nueva_hora:
            disponibles = get_available_slots(doctor_key, nueva_fecha)
            if nueva_hora not in disponibles:
                speak = f"La hora {nueva_hora} no está disponible. Las opciones son: {', '.join(disponibles[:4])}."
                return handler_input.response_builder.speak(speak).ask("¿Desea otra hora?").response
            session_attr["pending_action"] = "confirm_move"
            session_attr["pending_new_cita"] = {"fecha": nueva_fecha, "hora": nueva_hora}
            doc = get_doctor_info(doctor_key)
            speak = f"Confirma mover tu cita a {nueva_fecha} a las {nueva_hora} con {doc['nombre']}?"
            return handler_input.response_builder.speak(speak).ask(speak).response

        speak = "No entendí la solicitud para mover la cita."
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

# --- Info Doctor ---
class InfoDoctorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("InfoDoctorIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        doctor_raw = slots.get("doctor").value if slots.get("doctor") else None
        if not doctor_raw:
            speak = "¿Sobre qué doctor deseas información? Tenemos: Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response

        doctor_key = normalize_name(doctor_raw)
        doc_info = get_doctor_info(doctor_key)
        if not doc_info:
            speak = f"No encontré al doctor {doctor_raw}."
            return handler_input.response_builder.speak(speak).ask("¿Desea otro doctor?").response

        dias = ", ".join(doc_info["dias"])
        speak = f"{doc_info['nombre']} es especialista en {doc_info['especialidad']}. Atiende los días {dias} de {doc_info['inicio']}:00 a {doc_info['fin']}:00."
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

# --- Disponibilidad Doctor ---
class DisponibilidadDoctorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("DisponibilidadDoctorIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots or {}
        doctor_raw = slots.get("doctor").value if slots.get("doctor") else None
        fecha = slots.get("fecha").value if slots.get("fecha") else None

        if not doctor_raw:
            speak = "¿De qué doctor deseas saber la disponibilidad?"
            return handler_input.response_builder.speak(speak).ask(speak).response

        doctor_key = normalize_name(doctor_raw)
        doc_info = get_doctor_info(doctor_key)
        if not doc_info:
            speak = f"No encontré al doctor {doctor_raw}."
            return handler_input.response_builder.speak(speak).ask("¿Desea otro doctor?").response

        if not fecha:
            speak = "¿Para qué fecha necesitas la disponibilidad? Por favor indica la fecha (por ejemplo 2025-11-20)."
            return handler_input.response_builder.speak(speak).ask(speak).response

        disponibles = get_available_slots(doctor_key, fecha)
        if not disponibles:
            speak = f"No hay horarios disponibles para {doc_info['nombre']} el {fecha}."
            return handler_input.response_builder.speak(speak).ask("¿Deseas otra fecha?").response

        opciones = ", ".join(disponibles[:6])
        speak = f"Las horas disponibles para {doc_info['nombre']} el {fecha} son: {opciones}. ¿Quieres agendar alguna?"
        return handler_input.response_builder.speak(speak).ask("¿Deseas agendar alguna de estas horas?").response

# --- Yes / No handlers para confirmar acciones pendientes ---
class YesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        pending = session_attr.get("pending_action")

        user_key = session_attr.get("user_key")

        if pending == "confirm_agendar":
            pending_cita = session_attr.get("pending_cita")
            if not pending_cita:
                speak = "No tengo la información de la cita para agendar."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
            success = save_appointment(user_key, pending_cita["doctor"], pending_cita["fecha"], pending_cita["hora"])
            if success:
                doc = get_doctor_info(pending_cita["doctor"])
                speak = f"Listo — su cita con {doc['nombre']} quedó agendada para el {pending_cita['fecha']} a las {pending_cita['hora']}."
                # limpiar pending
                session_attr.pop("pending_cita", None)
                session_attr.pop("pending_action", None)
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
            else:
                speak = "Lo siento, la franja ya no está disponible. Intenta otra hora o fecha."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

        if pending == "confirm_cancel":
            success = cancel_appointment(user_key)
            if success:
                session_attr.pop("pending_action", None)
                speak = "Su cita ha sido cancelada correctamente."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
            else:
                speak = "No encontré una cita para cancelar."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

        if pending == "confirm_move":
            new = session_attr.get("pending_new_cita")
            success = move_appointment(user_key, new["fecha"], new["hora"])
            if success:
                doc = get_doctor_info(get_user_appointment(user_key)["doctor"])
                session_attr.pop("pending_action", None)
                session_attr.pop("pending_new_cita", None)
                speak = f"Su cita fue movida a {new['fecha']} a las {new['hora']}."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response
            else:
                speak = "No fue posible mover la cita a esa franja. Intente otra fecha u hora."
                return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

        if pending == "user_has_appointment":
            # si el usuario dijo que sí (por ejemplo sobre mover/cancel existía), pedimos aclarar si mover o cancelar
            speak = "¿Desea mover o cancelar la cita existente?"
            return handler_input.response_builder.speak(speak).ask("¿Mover o cancelar?").response

        speak = "De acuerdo."
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

class NoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr.pop("pending_action", None)
        session_attr.pop("pending_cita", None)
        session_attr.pop("pending_new_cita", None)
        speak = "De acuerdo, no se realizó ningún cambio. ¿Necesitas algo más?"
        return handler_input.response_builder.speak(speak).ask(REPROMPT_GENERIC).response

# --- Fallback ---
class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speak = "Disculpa, no entendí esa solicitud. Puedes decir: agendar cita, consultar mis citas, cancelar o mover una cita."
        return handler_input.response_builder.speak(speak).ask(speak).response

# --- SessionEnded ---
class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        # cleanup if needed
        return handler_input.response_builder.response

# --- Exception handler ---
class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error(exception, exc_info=True)
        speak = "Hubo un problema procesando tu solicitud. Por favor intenta de nuevo."
        return handler_input.response_builder.speak(speak).ask(speak).response
