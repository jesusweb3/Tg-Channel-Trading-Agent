# src/telegram/parser.py

from telethon import TelegramClient, events
from src.utils.config import config
from src.utils.logger import get_logger


class ChannelParser:
    """Парсер сообщений из Telegram канала"""

    def __init__(self, client: TelegramClient):
        self.logger = get_logger(__name__)
        self.client = client
        self.channel_id = int(config.CHANNEL_ID)

    async def start(self):
        """Запуск прослушивания канала"""
        try:
            entity = await self.client.get_entity(self.channel_id)
            channel_name = entity.title or "unknown"
        except Exception as e:
            self.logger.error(f'Ошибка получения имени канала: {e}')
            channel_name = "unknown"

        self.logger.info(f'Запуск парсера для канала {channel_name} (ID: {self.channel_id})')

        @self.client.on(events.NewMessage(chats=self.channel_id))
        async def handler(event):
            await self._handle_message(event)

        self.logger.info(f'Парсер активен, ожидание новых сообщений')

    async def _handle_message(self, event):
        """Обработка нового сообщения из канала"""
        try:
            message_text = event.message.text

            if not message_text:
                return

            self.logger.info(f'Получено сообщение из канала: {message_text}')

        except Exception as e:
            self.logger.error(f'Ошибка обработки сообщения: {e}', exc_info=True)