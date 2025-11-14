# lambda_function.py
import logging
from handlers import sb  # import SkillBuilder ya configurado
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lambda_handler = sb.lambda_handler()
