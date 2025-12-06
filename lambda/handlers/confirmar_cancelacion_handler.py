import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory
from strategies.response_format_strategy import ConfirmacionFormatStrategy

class ConfirmarCancelacionIntentHandler(AbstractRequestHandler):
    """Handler para confirmar la cancelación de cita"""
    
    def __init__(self, citas_service):
        self.citas_service = citas_service
        self.format_strategy = ConfirmacionFormatStrategy()
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConfirmarCancelacionIntent")(handler_input)
    
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        
        # Verificar que tengamos los datos necesarios
        if ("cancelar_doctor_id" not in session or 
            "cancelar_dia" not in session or 
            "cancelar_hora" not in session):
            return AlexaResponseFactory.create_ask_response(
                handler_input,
                "No tengo información de ninguna cita para cancelar. ¿Deseas cancelar una cita?",
                "Di cancelar cita con el nombre del doctor."
            )
        
        doctor_id = session.get("cancelar_doctor_id")
        dia = session.get("cancelar_dia")
        hora = session.get("cancelar_hora")
        
        # Cancelar la cita
        exito = self.citas_service.cancelar_cita(doctor_id, dia, hora)
        
        if not exito:
            return AlexaResponseFactory.create_error_response(
                handler_input,
                "Hubo un problema cancelando la cita. Intente nuevamente.",
                "¿Desea intentar de nuevo?"
            )
        
        # Limpiar datos de sesión
        session.pop("cancelar_doctor_id", None)
        session.pop("cancelar_dia", None)
        session.pop("cancelar_hora", None)
        
        # Formatear confirmación
        formatted = self.format_strategy.format({
            'tipo': 'cancelar',
            'dia': dia,
            'hora': hora
        })
        
        return AlexaResponseFactory.create_ask_response(
            handler_input,
            formatted['speech']
        )