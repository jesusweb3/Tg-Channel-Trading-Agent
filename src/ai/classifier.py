# src/ai/classifier.py

from src.ai.prompts import PromptManager
from src.ai.client import router_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def classify(message: str) -> str:
    """
    Классифицировать сообщение из канала

    Args:
        message: Текст сообщения из Telegram канала

    Returns:
        Классифицированный сигнал (одна строка)
    """
    try:
        prompt = PromptManager.build_prompt(message)
        result = await router_client.classify(prompt)
        return result

    except Exception as e:
        logger.error(f'Ошибка классификации сообщения: {e}', exc_info=True)
        raise