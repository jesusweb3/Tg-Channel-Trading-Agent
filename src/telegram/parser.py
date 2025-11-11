# src/telegram/parser.py

import asyncio
from telethon import TelegramClient
from src.utils.config import config
from src.utils.logger import get_logger
from src.ai.classifier import classify
from src.trading.signal_parser import parse
from src.trading.strategy import TradingStrategy

logger = get_logger(__name__)


class ChannelParser:
    """Парсер сообщений из Telegram канала с polling механизмом"""

    POLL_INTERVAL = 2
    POLL_LIMIT = 10

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
            logger.error(f'Ошибка получения имени канала: {type(e).__name__}: {e}', exc_info=True)
            channel_name = "unknown"

        logger.info(f'Запуск парсера для канала {channel_name} (ID: {self.channel_id})')

        # Инициализация: получить ID последних сообщений
        try:
            await self._init_processed_ids()
        except Exception as e:
            logger.error(f'Ошибка инициализации: {type(e).__name__}: {e}', exc_info=True)
            raise

        # Запуск polling loop и мониторинга
        asyncio.create_task(self._polling_loop())
        asyncio.create_task(self._monitor_connection())

        logger.info('Парсер активен, начинаем polling')

    async def _init_processed_ids(self) -> None:
        """Получить ID последних сообщений при старте"""
        logger.debug(f'Инициализация: получаю последние {self.POLL_LIMIT} сообщений из канала')

        messages = await self.client.get_messages(self.channel_id, limit=self.POLL_LIMIT)
        if messages:
            for msg in messages:
                self.processed_ids.add(msg.id)
            logger.info(
                f'Инициализация: сохранено {len(messages)} ID сообщений (от {messages[-1].id} до {messages[0].id})')
        else:
            logger.info('Канал пуст')

    async def _polling_loop(self) -> None:
        """Бесконечный polling каждые 2 секунды"""
        logger.info('_polling_loop: запущен')

        try:
            while True:
                await asyncio.sleep(self.POLL_INTERVAL)

                try:
                    logger.debug(f'Polling: получаю последние {self.POLL_LIMIT} сообщений')
                    messages = await self.client.get_messages(self.channel_id, limit=self.POLL_LIMIT)

                    if messages:
                        logger.debug(f'Polling: получено {len(messages)} сообщений, IDs: {[m.id for m in messages]}')

                        new_messages = [m for m in messages if m.id not in self.processed_ids]

                        if new_messages:
                            logger.debug(
                                f'Polling: найдено {len(new_messages)} новых сообщений, IDs: {[m.id for m in new_messages]}')

                            for message in reversed(new_messages):
                                self.processed_ids.add(message.id)
                                logger.debug(f'Polling: добавлено ID={message.id} в processed_ids')
                                await self._handle_message(message)
                        else:
                            logger.debug('Polling: нет новых сообщений')
                    else:
                        logger.debug('Polling: канал пуст')

                except asyncio.CancelledError:
                    logger.info('_polling_loop: получен сигнал отмены')
                    raise
                except Exception as e:
                    logger.error(f'_polling_loop: исключение {type(e).__name__}: {e}', exc_info=True)

        except asyncio.CancelledError:
            logger.info('Polling остановлен')
            raise

    async def _monitor_connection(self) -> None:
        """Мониторить состояние соединения"""
        logger.info('_monitor_connection: запущен')

        try:
            while True:
                is_connected = self.client.is_connected()
                logger.debug(f'Connection status: {is_connected}')

                if self._connection_state is None:
                    self._connection_state = is_connected
                    logger.debug(f'Connection state initialized: {is_connected}')
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
        except Exception as e:
            logger.error(f'_monitor_connection: исключение {type(e).__name__}: {e}', exc_info=True)
            raise

    async def _handle_message(self, message):
        """Обработка нового сообщения"""
        try:
            message_text = message.text
            message_id = message.id
            has_media = message.media is not None
            media_group_id = message.grouped_id

            logger.debug(
                f'_handle_message: ID={message_id}, text_len={len(message_text) if message_text else 0}, has_media={has_media}, media_group_id={media_group_id}')

            if not message_text:
                logger.debug(f'_handle_message: ID={message_id} без текста (только медиа), пропускаю')
                return

            escaped_text = message_text.replace('\n', '\\n')
            logger.info(f'Получено сообщение: {{text: "{escaped_text}"}}')

            logger.debug('_handle_message: отправляю на классификацию')
            ai_response = await classify(message_text)
            logger.debug(f'_handle_message: ответ от AI: {ai_response}')

            logger.debug('_handle_message: парсю сигнал')
            signal = parse(ai_response)
            logger.debug(f'_handle_message: распарсенный сигнал: {signal}')

            logger.debug('_handle_message: обрабатываю сигнал в стратегии')
            await self.strategy.process_signal(signal)
            logger.debug('_handle_message: сигнал обработан успешно')

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f'_handle_message: исключение {type(e).__name__}: {e}', exc_info=True)