# src/utils/config.py

import os
from dotenv import load_dotenv
from src.utils.logger import get_logger

load_dotenv()


class OpenRouterConfig:
    """Конфигурация OpenRouter API"""

    def __init__(self):
        self.API_KEY = self._get_required('OPENROUTER_API_KEY')
        self.MODEL = self._get_required('OPENROUTER_MODEL')

    @staticmethod
    def _get_required(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f'Требуемая переменная окружения {key} не установлена')
        return value


class BybitConfig:
    """Конфигурация Bybit API"""

    def __init__(self):
        self.API_KEY = self._get_required('BYBIT_API_KEY')
        self.API_SECRET = self._get_required('BYBIT_API_SECRET')

    @staticmethod
    def _get_required(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f'Требуемая переменная окружения {key} не установлена')
        return value


class Config:
    def __init__(self):
        self.API_ID = self._get_required('TELETHON_API_ID')
        self.API_HASH = self._get_required('TELETHON_API_HASH')
        self.PHONE_NUMBER = self._get_required('PHONE_NUMBER')
        self.CHANNEL_ID = self._get_required('TELETHON_CHANNEL_ID')
        self.PASSWORD = os.getenv('FA_PASSWORD', '')

        self.openrouter = OpenRouterConfig()
        self.bybit = BybitConfig()

        self.BALANCE = self._get_positive_float('BALANCE')
        self.AMOUNT = self._get_amount_percentage()

        logger = get_logger(__name__)
        logger.info('Инициализация конфига успешна')

    @staticmethod
    def _get_required(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f'Требуемая переменная окружения {key} не установлена')
        return value

    @staticmethod
    def _get_positive_float(key: str) -> float:
        value = os.getenv(key)
        if not value:
            raise ValueError(f'Требуемая переменная окружения {key} не установлена')
        try:
            num = float(value)
            if num <= 0:
                raise ValueError(f'{key} должен быть больше 0')
            return num
        except ValueError as e:
            raise ValueError(f'{key} должен быть числом больше 0: {e}')

    @staticmethod
    def _get_amount_percentage() -> float:
        value = os.getenv('AMOUNT')
        if not value:
            raise ValueError('Требуемая переменная окружения AMOUNT не установлена')
        try:
            num = float(value)
            if num < 0 or num > 100:
                raise ValueError(f'AMOUNT должен быть от 0 до 100, получено: {num}')
            return num
        except ValueError as e:
            raise ValueError(f'AMOUNT должен быть числом от 0 до 100: {e}')


config = Config()