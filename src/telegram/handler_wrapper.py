# src/telegram/handler_wrapper.py

import asyncio
from typing import Callable
from functools import wraps
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HandlerStats:
    """Статистика обработки сообщений"""

    def __init__(self):
        self.total_processed = 0
        self.successful = 0
        self.failed = 0
        self.consecutive_failures = 0

    def record_success(self) -> None:
        self.total_processed += 1
        self.successful += 1
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.total_processed += 1
        self.failed += 1
        self.consecutive_failures += 1

    def get_stats(self) -> str:
        success_rate = (self.successful / self.total_processed * 100) if self.total_processed > 0 else 0
        return f'Обработано: {self.total_processed} | Успешно: {self.successful} | Ошибок: {self.failed} | Ошибок подряд: {self.consecutive_failures} | Успешность: {success_rate:.1f}%'


handler_stats = HandlerStats()


def safe_handler(func: Callable) -> Callable:
    """
    Декоратор для безопасной обработки Telegram событий.

    Гарантирует:
    - Все исключения будут пойманы
    - Все будут залогированы с контекстом
    - Handler НИКОГДА не упадёт
    - Ведётся статистика
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> None:
        event = args[0] if args else None
        message_text = None

        try:
            # Извлекаем текст сообщения для логирования
            if event and hasattr(event, 'message') and hasattr(event.message, 'text'):
                message_text = event.message.text
                if message_text:
                    escaped_text = message_text.replace('\n', '\\n')[:100]
                    logger.info(f'[STAGE: received] Получено сообщение: "{escaped_text}"')

            # Вызываем оригинальный handler
            await func(*args, **kwargs)

            # Если мы здесь - всё успешно
            handler_stats.record_success()
            logger.info(f'[STAGE: success] Обработано успешно | Stats: {handler_stats.get_stats()}')

        except asyncio.CancelledError:
            raise

        except Exception as e:
            handler_stats.record_failure()
            error_type = type(e).__name__
            error_msg = str(e)

            logger.error(
                f'[STAGE: error] Ошибка обработки\n'
                f'  Type: {error_type}\n'
                f'  Msg: {error_msg}\n'
                f'  Text: {message_text[:100] if message_text else "N/A"}\n'
                f'  Stats: {handler_stats.get_stats()}',
                exc_info=True
            )

    return wrapper


def get_handler_stats() -> str:
    """Получить текущую статистику обработки"""
    return handler_stats.get_stats()