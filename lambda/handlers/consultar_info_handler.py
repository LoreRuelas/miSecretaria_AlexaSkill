import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory
from strategies.response_format_strategy import ConsultarInfoFormatStrategy

class ConsultarInfoIntentHandler(AbstractRequestHandler):
    """Handler para consultar información de un doctor específico"""
    
    def __init__(self, citas_service):
        self.citas_service = citas_service
        self.format_strategy = ConsultarInfoFormatStrategy()
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConsultarInfoIntent")(handler_input)
    
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        doctor_slot = slots.get("doctor")
        
        # Intentar obtener el valor del slot
        doctor = None
        if doctor_slot:
            if doctor_slot.value:
                doctor = doctor_slot.value
            elif (hasattr(doctor_slot, 'resolutions') and 
                  doctor_slot.resolutions and
                  doctor_slot.resolutions.resolutions_per_authority):
                doctor = doctor_slot.resolutions.resolutions_per_authority[0].values[0].value.name
        
        if not doctor:
            return AlexaResponseFactory.create_ask_response(
                handler_input,
                "¿De qué doctor deseas consultar información? Tenemos a Ramírez, Gómez y Hernández."
            )
        
        # Buscar doctor
        doctor_info = self.citas_service.buscar_doctor(doctor)
        if not doctor_info:
            return AlexaResponseFactory.create_ask_response(
                handler_input,
                f"No encuentro al doctor {doctor}. Puede elegir entre Ramírez, Gómez o Hernández.",
                "¿De quién deseas información?"
            )
        
        # Formatear usando Strategy
        formatted = self.format_strategy.format({
            'doctor': doctor_info
        })
        
        return AlexaResponseFactory.create_ask_response(
            handler_input,
            formatted['speech'],
            "¿Desea hacer algo más?"
        )