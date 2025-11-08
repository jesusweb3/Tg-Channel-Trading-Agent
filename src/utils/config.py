# src/utils/config.py

import os
from dotenv import load_dotenv
from src.utils.logger import get_logger

load_dotenv()


class Config:
    def __init__(self):
        self.API_ID = self._get_required('TELETHON_API_ID')
        self.API_HASH = self._get_required('TELETHON_API_HASH')
        self.PHONE_NUMBER = self._get_required('PHONE_NUMBER')
        self.CHANNEL_ID = self._get_required('TELETHON_CHANNEL_ID')

        self.PASSWORD = os.getenv('FA_PASSWORD', '')

        logger = get_logger(__name__)
        logger.info('Инициализация конфига успешна')

    @staticmethod
    def _get_required(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f'Требуемая переменная окружения {key} не установлена')
        return value


config = Config()