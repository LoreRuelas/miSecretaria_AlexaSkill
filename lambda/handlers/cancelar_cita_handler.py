import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory
from strategies.response_format_strategy import CitasOcupadasFormatStrategy

logger = logging.getLogger(__name__)

class CancelarCitaIntentHandler(AbstractRequestHandler):
    """Handler para iniciar el proceso de cancelación"""
    
    def __init__(self, citas_service):
        self.citas_service = citas_service
        self.format_strategy = CitasOcupadasFormatStrategy()
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("CancelarCitaIntent")(handler_input)
    
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
                "¿Con qué doctor deseas cancelar tu cita? Puedes decir Ramírez, Gómez o Hernández."
            )
        
        # Buscar doctor
        doctor_info = self.citas_service.buscar_doctor(doctor)
        if not doctor_info:
            return AlexaResponseFactory.create_ask_response(
                handler_input,
                f"No encuentro al doctor {doctor}. Intenta nuevamente.",
                "¿Con quién deseas cancelar?"
            )
        
        # Obtener citas ocupadas
        try:
            citas_ocupadas = self.citas_service.obtener_citas_ocupadas(doctor_info.id)
        except Exception as e:
            logger.error("Error al obtener citas ocupadas: %s", e, exc_info=True)
            return AlexaResponseFactory.create_error_response(
                handler_input,
                "Hubo un problema obteniendo las citas. Intente nuevamente.",
                "¿Con quién deseas cancelar?"
            )
        
        # Formatear usando Strategy
        formatted = self.format_strategy.format({
            'doctor_nombre': doctor_info.nombre,
            'citas': citas_ocupadas
        })
        
        if not formatted['cita']:
            return AlexaResponseFactory.create_tell_response(
                handler_input,
                formatted['speech']
            )
        
        # Guardar en sesión
        session = handler_input.attributes_manager.session_attributes
        session["cancelar_doctor_id"] = doctor_info.id
        session["cancelar_dia"] = formatted['cita'][0]
        session["cancelar_hora"] = formatted['cita'][1]
        
        return AlexaResponseFactory.create_ask_response(
            handler_input,
            formatted['speech']
        )