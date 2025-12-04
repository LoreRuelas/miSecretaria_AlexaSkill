import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_model import Response

from data_manager import get_doctor_info, get_citas_ocupadas, ocupar_cita

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speak_output = (
            "Bienvenido a la clínica. Soy su secretaria virtual. "
            "¿Desea agendar una cita o consultar información?"
        )
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class AgendarCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AgendarCitaIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        doctor = slots.get("doctor").value if slots.get("doctor") else None

        if not doctor:
            speak = "Claro, ¿con qué doctor desea agendar la cita? Tenemos a Ramírez, Gómez y Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response

        info = get_doctor_info(doctor)
        if not info:
            speak = f"No encuentro al doctor {doctor}. Puede elegir entre Ramírez, Gómez o Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response

        citas = info.get_citas_disponibles()
        if not citas:
            return handler_input.response_builder.speak("Ese doctor no tiene citas disponibles.").response

        session = handler_input.attributes_manager.session_attributes
        session["doctor_id"] = info.id

        # Crear dict {A:(dia,hora), B:(dia,hora)...}
        opciones = {}
        speak_list = ""
        letras = ["A","B","C","D","E","F"]  # suficiente para varias citas

        for i, c in enumerate(citas):
            letra = letras[i]
            opciones[letra] = (c.dia, c.hora)
            speak_list += f"Opción {letra}: {c.dia} a las {c.hora}. "

        session["citas"] = opciones

        speak = f"Perfecto, estas son las citas disponibles con {info.nombre}: {speak_list} " \
                "Indique la opción que desea, por ejemplo diga: opción A."
                
        return handler_input.response_builder.speak(speak).ask(speak).response



# ================== PASO 2: Usuario elige un número ==================
class ElegirCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ElegirCitaIntent")(handler_input)

    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes

        opcion = ask_utils.get_slot_value(handler_input, "opcion")
        if not opcion:
            speak = "No entendí qué opción desea. Diga por ejemplo opción A."
            return handler_input.response_builder.speak(speak).ask(speak).response

        opcion = opcion.upper()

        if "citas" not in session or opcion not in session["citas"]:
            speak = "Esa opción no está disponible. Intente con otra."
            return handler_input.response_builder.speak(speak).ask(speak).response

        doctor_id = session.get("doctor_id")
        dia, hora = session["citas"][opcion]

        # 🔥 Marcar cita como ocupada en data_manager
        from data_manager import ocupar_cita
        ocupar_cita(doctor_id, dia, hora)

        speak = f"Cita agendada con éxito el {dia} a las {hora}. ¿Desea hacer algo más?"
        return handler_input.response_builder.speak(speak).ask("¿Desea algo más?").response

class CancelarCitaIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("CancelarCitaIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        # obtener el slot doctor (si viene en la misma utterance)
        doctor_slot = slots.get("doctor")
        doctor = doctor_slot.value if doctor_slot and doctor_slot.value else None

        # Si no especificó doctor, preguntamos
        if not doctor:
            speak = "¿Con qué doctor deseas cancelar tu cita? Puedes decir Ramírez, Gómez o Hernández."
            return handler_input.response_builder.speak(speak).ask(speak).response

        # Normalizar nombre y obtener info
        info = get_doctor_info(doctor)
        if not info:
            return handler_input.response_builder.speak(
                f"No encuentro al doctor {doctor}. Intenta nuevamente."
            ).ask("¿Con quién deseas cancelar?").response

        # obtenemos citas ocupadas (usa la función importada)
        try:
            citas_ocupadas = get_citas_ocupadas(info.id)
        except Exception as e:
            logger.error("Error al obtener citas ocupadas: %s", e, exc_info=True)
            return handler_input.response_builder.speak(
                "Hubo un problema obteniendo las citas. Intente nuevamente."
            ).ask("¿Con quién deseas cancelar?").response

        if not citas_ocupadas:
            return handler_input.response_builder.speak(
                f"El doctor {info.nombre} no tiene citas registradas como ocupadas."
            ).response

        session = handler_input.attributes_manager.session_attributes
        session["cancelar_doctor_id"] = info.id

        # Crear lista tipo A,B,C...
        opciones = {}
        letras = ["A","B","C","D","E","F","G","H"]
        speak_list = ""

        for i, c in enumerate(citas_ocupadas):
            letra = letras[i]
            opciones[letra] = (c.dia, c.hora)
            speak_list += f"Opción {letra}: {c.dia} a las {c.hora}. "

        session["cancelar_citas"] = opciones

        speak = f"Tienes estas citas con {info.nombre}: {speak_list} ¿Cuál deseas cancelar? Di por ejemplo opción A."
        return handler_input.response_builder.speak(speak).ask(speak).response


class ConfirmarCancelacionIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConfirmarCancelacionIntent")(handler_input)

    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        opcion = ask_utils.get_slot_value(handler_input, "opcion")

        if not opcion or "cancelar_citas" not in session:
            speak = "No entendí qué opción deseas cancelar. Dime por ejemplo opción A."
            return (
                handler_input.response_builder
                .speak(speak)
                .ask(speak)
                .response
            )

        opcion = opcion.upper()

        if opcion not in session["cancelar_citas"]:
            return (
                handler_input.response_builder
                .speak("Esa opción no existe, intenta con otra.")
                .ask("Indica la opción.")
                .response
            )

        doctor_id = session.get("cancelar_doctor_id")
        dia, hora = session["cancelar_citas"][opcion]

        # 🔥 Cancelar cita real en memoria
        from data_manager import cancelar_cita
        cancelar_cita(doctor_id, dia, hora)

        speak = f"La cita del {dia} a las {hora} ha sido cancelada."
        return (
            handler_input.response_builder
            .speak(speak)
            .ask("¿Deseas hacer algo más?")
            .response
        )



class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error(exception, exc_info=True)
        speak_output = "Hubo un problema procesando su solicitud. Por favor intente de nuevo."
        return handler_input.response_builder.speak(speak_output).ask(speak_output).response
