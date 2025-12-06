import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_model import Response

logger = logging.getLogger(__name__)

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler para cuando termina la sesión"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Handler global para excepciones"""
    
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True
    
    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error(exception, exc_info=True)
        speak_output = "Hubo un problema procesando su solicitud. Por favor intente de nuevo."
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


