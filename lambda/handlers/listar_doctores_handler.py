import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory
from strategies.response_format_strategy import ListarDoctoresFormatStrategy

class ListarDoctoresIntentHandler(AbstractRequestHandler):
    """Handler para listar todos los doctores disponibles"""
    
    def __init__(self, citas_service):
        self.citas_service = citas_service
        self.format_strategy = ListarDoctoresFormatStrategy()
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ListarDoctoresIntent")(handler_input)
    
    def handle(self, handler_input):
        # Obtener todos los doctores
        doctores = self.citas_service.obtener_todos_doctores()
        
        # Formatear usando Strategy
        formatted = self.format_strategy.format({
            'doctores': doctores
        })
        
        return AlexaResponseFactory.create_ask_response(
            handler_input,
            formatted['speech'],
            "¿Desea hacer algo más?"
        )