import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory
from strategies.response_format_strategy import ConfirmacionFormatStrategy

class ElegirCitaIntentHandler(AbstractRequestHandler):
    """Handler para confirmar la selección de cita"""
    
    def __init__(self, citas_service):
        self.citas_service = citas_service
        self.format_strategy = ConfirmacionFormatStrategy()
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ElegirCitaIntent")(handler_input)
    
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        opcion = ask_utils.get_slot_value(handler_input, "opcion")
        
        if not opcion:
            return AlexaResponseFactory.create_ask_response(
                handler_input,
                "No entendí qué opción desea. Diga por ejemplo opción A."
            )
        
        opcion = opcion.upper()
        
        if "citas" not in session or opcion not in session["citas"]:
            return AlexaResponseFactory.create_ask_response(
                handler_input,
                "Esa opción no está disponible. Intente con otra."
            )
        
        doctor_id = session.get("doctor_id")
        dia, hora = session["citas"][opcion]
        
        # Agendar la cita
        exito = self.citas_service.agendar_cita(doctor_id, dia, hora)
        
        if not exito:
            return AlexaResponseFactory.create_error_response(
                handler_input,
                "Hubo un problema agendando la cita. Intente nuevamente.",
                "¿Desea intentar con otra opción?"
            )
        
        # Formatear confirmación
        formatted = self.format_strategy.format({
            'tipo': 'agendar',
            'dia': dia,
            'hora': hora
        })
        
        return AlexaResponseFactory.create_ask_response(
            handler_input,
            formatted['speech']
        )

