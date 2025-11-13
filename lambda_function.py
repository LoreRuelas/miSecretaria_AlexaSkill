import logging
from ask_sdk_core.skill_builder import SkillBuilder

from handlers import (
    LaunchRequestHandler,
    RegistrarUsuarioIntentHandler,
    AgendarCitaIntentHandler,
    ConsultarCitasIntentHandler,
    CancelarCitaIntentHandler,
    MoverCitaIntentHandler,
    InfoDoctorIntentHandler,
    DisponibilidadDoctorIntentHandler,
    YesIntentHandler,
    NoIntentHandler,
    FallbackIntentHandler,
    SessionEndedRequestHandler,
    CatchAllExceptionHandler
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sb = SkillBuilder()

# Request handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(RegistrarUsuarioIntentHandler())
sb.add_request_handler(AgendarCitaIntentHandler())
sb.add_request_handler(ConsultarCitasIntentHandler())
sb.add_request_handler(CancelarCitaIntentHandler())
sb.add_request_handler(MoverCitaIntentHandler())
sb.add_request_handler(InfoDoctorIntentHandler())
sb.add_request_handler(DisponibilidadDoctorIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
