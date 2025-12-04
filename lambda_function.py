import logging
from ask_sdk_core.skill_builder import SkillBuilder

from handlers import (
    LaunchRequestHandler, 
    AgendarCitaIntentHandler,
    ElegirCitaIntentHandler,
    CancelarCitaIntentHandler,
    ConfirmarCancelacionIntentHandler,
    SessionEndedRequestHandler,
    CatchAllExceptionHandler
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ❗ Temporalmente sin persistencia para debug
# from ask_sdk_core.persistence_adapter import DynamoDbPersistenceAdapter
# persistence_adapter = DynamoDbPersistenceAdapter(
#     table_name="citas_skill_table",
#     create_table=True
# )
# sb = SkillBuilder(persistence_adapter=persistence_adapter)

sb = SkillBuilder()  # ✅ así iniciamos sin errores

# Handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AgendarCitaIntentHandler())
sb.add_request_handler(ElegirCitaIntentHandler())
sb.add_request_handler(CancelarCitaIntentHandler())
sb.add_request_handler(ConfirmarCancelacionIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

# Lambda handler
lambda_handler = sb.lambda_handler()
