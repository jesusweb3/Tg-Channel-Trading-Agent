# src/telegram/auth.py

from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TelegramAuth:
    SESSION_DIR = Path(__file__).parent
    SESSION_NAME = 'session'

    DEVICE_MODEL = 'SM-S921B'
    SYSTEM_VERSION = '14'
    APP_VERSION = '10.13.0 x64'
    LANG_CODE = 'en'

    def __init__(self):
        self.client = None

    async def get_client(self) -> TelegramClient:
        """Получить авторизованный Telegram клиент"""
        if self.client and self.client.is_connected():
            return self.client

        session_path = self.SESSION_DIR / self.SESSION_NAME

        self.client = TelegramClient(
            str(session_path),
            config.API_ID,
            config.API_HASH,
            device_model=self.DEVICE_MODEL,
            system_version=self.SYSTEM_VERSION,
            app_version=self.APP_VERSION,
            lang_code=self.LANG_CODE
        )

        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self._authorize()

        me = await self.client.get_me()
        logger.info(f'Авторизован как: {me.first_name}')

        return self.client

    async def _authorize(self) -> None:
        """Авторизация при первом запуске"""
        logger.info('Начало авторизации в Telegram')

        await self.client.send_code_request(config.PHONE_NUMBER)
        logger.info(f'Код отправлен на номер {config.PHONE_NUMBER}')

        code = input('Введите код подтверждения: ')

        try:
            await self.client.sign_in(config.PHONE_NUMBER, code)
        except SessionPasswordNeededError:
            await self.client.sign_in(password=config.PASSWORD)

        logger.info('Авторизация успешна')

    async def disconnect(self) -> None:
        """Отключение от Telegram"""
        if self.client:
            await self.client.disconnect()
            self.client = None
            logger.info('Отключение от Telegram')


auth = TelegramAuth()