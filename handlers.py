import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_model import Response
import unicodedata


from data_manager import get_doctor_info  # ✅ sin punto

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
        intent = handler_input.request_envelope.request.intent
        slots = intent.slots

        doctor = slots.get("doctor").value if slots.get("doctor") else None
        fecha = slots.get("fecha").value if slots.get("fecha") else None
        hora = slots.get("hora").value if slots.get("hora") else None

        # Validación de que los 3 slots existan
        if not doctor or not fecha or not hora:
            speak_output = (
                "Para agendar, necesito el nombre del doctor, la fecha y la hora. "
                "Por favor diga: agendar cita con el doctor, día y hora."
            )
            return handler_input.response_builder.speak(speak_output).ask(speak_output).response

        # Validación de doctor permitido
        doctores_validos = ["ramirez", "gomez", "hernandez"]
        doctor_normalizado = doctor.lower().replace("dr ", "").replace("doctor ", "")

        if doctor_normalizado not in doctores_validos:
            speak_output = (
                f"Lo siento, no tengo registrado al doctor {doctor}. "
                "Los doctores disponibles son Ramírez, Gómez y Hernández."
            )
            return handler_input.response_builder.speak(speak_output).ask("¿Desea intentar con otro doctor?").response

        # TODO — Aquí puedes agregar lógica para guardar la cita en tu base/agenda
        
        speak_output = (
            f"Cita agendada con el doctor {doctor} el {fecha} a las {hora}. "
            "¿Desea algo más?"
        )
        return handler_input.response_builder.speak(speak_output).ask("¿Necesita algo más?").response


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
