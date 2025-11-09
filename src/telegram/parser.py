# src/telegram/parser.py

from telethon import TelegramClient, events
from src.utils.config import config
from src.utils.logger import get_logger
from src.ai.classifier import classify

logger = get_logger(__name__)


class ChannelParser:
    """Парсер сообщений из Telegram канала"""

    def __init__(self, client: TelegramClient):
        self.client = client
        self.channel_id = int(config.CHANNEL_ID)

    async def start(self):
        """Запуск прослушивания канала"""
        try:
            entity = await self.client.get_entity(self.channel_id)
            channel_name = entity.title or "unknown"
        except Exception as e:
            logger.error(f'Ошибка получения имени канала: {e}')
            channel_name = "unknown"

        logger.info(f'Запуск парсера для канала {channel_name} (ID: {self.channel_id})')

        @self.client.on(events.NewMessage(chats=self.channel_id))
        async def handler(event):
            await self._handle_message(event)

        logger.info(f'Парсер активен, ожидание новых сообщений')

    @staticmethod
    async def _handle_message(event):
        """Обработка нового сообщения из канала"""
        try:
            message_text = event.message.text

            if not message_text:
                return

            escaped_text = message_text.replace('\n', '\\n')
            logger.info(f'Получено сообщение из канала: {{text: "{escaped_text}"}}')

            await classify(message_text)

        except Exception as e:
            logger.error(f'Ошибка обработки сообщения: {e}', exc_info=True)