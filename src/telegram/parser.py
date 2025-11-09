# src/telegram/parser.py

from telethon import TelegramClient, events
from src.utils.config import config
from src.utils.logger import get_logger
from src.ai.classifier import classify
from src.trading.signal_parser import parse
from src.trading.strategy import TradingStrategy

logger = get_logger(__name__)


class ChannelParser:
    """Парсер сообщений из Telegram канала с обработкой торговых сигналов"""

    def __init__(self, client: TelegramClient, strategy: TradingStrategy):
        self.client = client
        self.channel_id = int(config.CHANNEL_ID)
        self.strategy = strategy

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

        logger.info('Парсер активен, ожидание новых сообщений')

    async def _handle_message(self, event):
        """Обработка нового сообщения из канала"""
        try:
            message_text = event.message.text

            if not message_text:
                return

            escaped_text = message_text.replace('\n', '\\n')
            logger.info(f'Получено сообщение из канала: {{text: "{escaped_text}"}}')

            # Классифицировать сообщение через ИИ
            ai_response = await classify(message_text)

            # Распарсить ответ ИИ в сигнал
            signal = parse(ai_response)

            # Обработать сигнал стратегией
            await self.strategy.process_signal(signal)

        except Exception as e:
            logger.error(f'Ошибка обработки сообщения: {e}', exc_info=True)