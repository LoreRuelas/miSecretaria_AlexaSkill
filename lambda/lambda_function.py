import logging
from ask_sdk_core.skill_builder import SkillBuilder

# Importar handlers
from handlers.launch_handler import LaunchRequestHandler
from handlers.agendar_cita_handler import AgendarCitaIntentHandler
from handlers.elegir_cita_handler import ElegirCitaIntentHandler
from handlers.cancelar_cita_handler import CancelarCitaIntentHandler
from handlers.confirmar_cancelacion_handler import ConfirmarCancelacionIntentHandler
from handlers.consultar_info_handler import ConsultarInfoIntentHandler
from handlers.listar_doctores_handler import ListarDoctoresIntentHandler
from handlers.common_handlers import SessionEndedRequestHandler, CatchAllExceptionHandler

# Importar servicios y repositorios
from repositories.doctor_repository import DoctorRepository
from services.citas_service import CitasService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ===== Inicializar dependencias (Dependency Injection) =====
doctor_repository = DoctorRepository()
citas_service = CitasService(doctor_repository)

# ===== Inicializar SkillBuilder =====
sb = SkillBuilder()

# ===== Registrar handlers con sus dependencias =====
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AgendarCitaIntentHandler(citas_service))
sb.add_request_handler(ElegirCitaIntentHandler(citas_service))
sb.add_request_handler(CancelarCitaIntentHandler(citas_service))
sb.add_request_handler(ConfirmarCancelacionIntentHandler(citas_service))
sb.add_request_handler(ConsultarInfoIntentHandler(citas_service))
sb.add_request_handler(ListarDoctoresIntentHandler(citas_service))
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

# ===== Lambda handler =====
lambda_handler = sb.lambda_handler()