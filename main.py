# main.py

import asyncio
from src.telegram.auth import auth
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    try:
        logger.info('Запуск приложения')

        await auth.get_client()

        await auth.disconnect()
        logger.info('Приложение завершено успешно')

    except Exception as e:
        logger.error(f'Ошибка: {e}')


if __name__ == '__main__':
    asyncio.run(main())