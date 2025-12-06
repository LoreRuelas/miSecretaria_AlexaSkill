from ask_sdk_model import Response

class AlexaResponseFactory:
    """
    FACTORY METHOD PATTERN: Crea diferentes tipos de respuestas de Alexa
    Centraliza la lógica de creación de respuestas
    """
    
    @staticmethod
    def create_ask_response(handler_input, speech_text, reprompt_text=None):
        """Crea una respuesta que espera input del usuario"""
        if reprompt_text is None:
            reprompt_text = speech_text
        
        return (
            handler_input.response_builder
            .speak(speech_text)
            .ask(reprompt_text)
            .response
        )
    
    @staticmethod
    def create_tell_response(handler_input, speech_text):
        """Crea una respuesta que termina la sesión"""
        return (
            handler_input.response_builder
            .speak(speech_text)
            .response
        )
    
    @staticmethod
    def create_error_response(handler_input, error_message, reprompt=None):
        """Crea una respuesta de error"""
        if reprompt:
            return AlexaResponseFactory.create_ask_response(
                handler_input, error_message, reprompt
            )
        return AlexaResponseFactory.create_tell_response(handler_input, error_message)
    
    @staticmethod
    def create_success_response(handler_input, success_message, continue_conversation=True):
        """Crea una respuesta de éxito"""
        if continue_conversation:
            return AlexaResponseFactory.create_ask_response(
                handler_input, 
                success_message,
                "¿Desea hacer algo más?"
            )
        return AlexaResponseFactory.create_tell_response(handler_input, success_message)

