import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler para el inicio de la skill"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input: HandlerInput):
        speak_output = (
            "Bienvenido a la clínica. Soy su secretaria virtual. "
            "¿Desea agendar una cita o consultar información?"
        )
        return AlexaResponseFactory.create_ask_response(
            handler_input, speak_output
        )

