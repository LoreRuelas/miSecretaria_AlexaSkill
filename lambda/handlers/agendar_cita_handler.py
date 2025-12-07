import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from factories.response_factory import AlexaResponseFactory
from strategies.response_format_strategy import CitasDisponiblesFormatStrategy

class AgendarCitaIntentHandler(AbstractRequestHandler):
    """Handler para iniciar el proceso de agendar cita"""
    
    def __init__(self, citas_service):
        self.citas_service = citas_service
        self.format_strategy = CitasDisponiblesFormatStrategy()
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AgendarCitaIntent")(handler_input)
    
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        doctor = slots.get("doctor").value if slots.get("doctor") else None
        
        # Si no especificó doctor, preguntar
        if not doctor:
            speak = "Claro, ¿con qué doctor desea agendar la cita? Tenemos a Ramírez, Gómez y Hernández."
            return AlexaResponseFactory.create_ask_response(handler_input, speak)
        
        # Buscar doctor
        doctor_info = self.citas_service.buscar_doctor(doctor)
        if not doctor_info:
            speak = f"No encuentro al doctor {doctor}. Puede elegir entre Ramírez, Gómez o Hernández."
            return AlexaResponseFactory.create_ask_response(handler_input, speak)
        
        # Obtener citas disponibles
        citas_disponibles = self.citas_service.obtener_citas_disponibles(doctor_info.id)
        
        if not citas_disponibles:
            return AlexaResponseFactory.create_tell_response(
                handler_input,
                f"{doctor_info.nombre} no tiene citas disponibles."
            )
        
        # Formatear respuesta usando Strategy
        formatted = self.format_strategy.format({
            'doctor_nombre': doctor_info.nombre,
            'citas': citas_disponibles
        })
        
        # Guardar en sesión
        session = handler_input.attributes_manager.session_attributes
        session["doctor_id"] = doctor_info.id
        session["citas"] = formatted['opciones']
        
        return AlexaResponseFactory.create_ask_response(
            handler_input, 
            formatted['speech']
        )

