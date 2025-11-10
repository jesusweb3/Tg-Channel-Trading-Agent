# src/telegram/parser.py

import asyncio
from telethon import TelegramClient
from src.utils.config import config
from src.utils.logger import get_logger
from src.ai.classifier import classify
from src.trading.signal_parser import parse
from src.trading.strategy import TradingStrategy
from src.telegram.handler_wrapper import safe_handler

logger = get_logger(__name__)


class _MessageEvent:
    """Wrapper для совместимости с _handle_message"""

    def __init__(self, message):
        self.message = message


class ChannelParser:
    """Парсер сообщений из Telegram канала с polling механизмом"""

    POLL_INTERVAL = 2

    def __init__(self, client: TelegramClient, strategy: TradingStrategy):
        self.client = client
        self.channel_id = int(config.CHANNEL_ID)
        self.strategy = strategy
        self.processed_ids: set[int] = set()
        self._connection_state: bool | None = None

    async def start(self) -> None:
        """Запуск парсера с polling механизмом"""
        try:
            entity = await self.client.get_entity(self.channel_id)
            channel_name = entity.title or "unknown"
        except Exception as e:
            logger.error(f'Ошибка получения имени канала: {e}')
            channel_name = "unknown"

        logger.info(f'Запуск парсера для канала {channel_name} (ID: {self.channel_id})')

        # Инициализация: получить ID последнего сообщения
        try:
            await self._init_processed_ids()
        except Exception as e:
            logger.error(f'Ошибка инициализации: {e}')
            raise

        # Запуск polling loop и мониторинга
        asyncio.create_task(self._polling_loop())
        asyncio.create_task(self._monitor_connection())

        logger.info('Парсер активен, начинаем polling')

    async def _init_processed_ids(self) -> None:
        """Получить ID последнего сообщения при старте"""
        messages = await self.client.get_messages(self.channel_id, limit=1)
        if messages:
            last_id = messages[0].id
            self.processed_ids.add(last_id)
            logger.info(f'Инициализация: последнее сообщение ID={last_id}')
        else:
            logger.info('Канал пуст')

    async def _polling_loop(self) -> None:
        """Бесконечный polling каждые 2 секунды"""
        try:
            while True:
                await asyncio.sleep(self.POLL_INTERVAL)

                try:
                    messages = await self.client.get_messages(self.channel_id, limit=1)
                    if messages:
                        message = messages[0]
                        if message.id not in self.processed_ids:
                            self.processed_ids.add(message.id)
                            event = _MessageEvent(message)
                            await self._handle_message(event)

                except Exception as e:
                    logger.error(f'Ошибка polling: {e}')

        except asyncio.CancelledError:
            logger.info('Polling остановлен')
            raise

    async def _monitor_connection(self) -> None:
        """Мониторить состояние соединения"""
        try:
            while True:
                is_connected = self.client.is_connected()

                if self._connection_state is None:
                    self._connection_state = is_connected
                elif self._connection_state != is_connected:
                    if is_connected:
                        logger.info('Telethon: соединение восстановлено')
                    else:
                        logger.warning('Telethon: соединение потеряно')
                    self._connection_state = is_connected

                await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info('Мониторинг остановлен')
            raise

    @safe_handler
    async def _handle_message(self, event):
        """Обработка нового сообщения"""
        message_text = event.message.text

        if not message_text:
            return

        escaped_text = message_text.replace('\n', '\\n')
        logger.info(f'Получено сообщение: {{text: "{escaped_text}"}}')

        ai_response = await classify(message_text)
        signal = parse(ai_response)
        await self.strategy.process_signal(signal)