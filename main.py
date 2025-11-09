# main.py

import asyncio
from src.telegram.auth import auth
from src.telegram.parser import ChannelParser
from src.ai.client import router_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    try:
        logger.info('Запуск приложения')

        client = await auth.get_client()
        await router_client.init()

        parser = ChannelParser(client)
        await parser.start()

        await asyncio.sleep(float('inf'))

    except asyncio.CancelledError:
        logger.info('Получен сигнал остановки')
    except Exception as e:
        logger.error(f'Ошибка: {e}', exc_info=True)
    finally:
        await auth.disconnect()
        await router_client.disconnect()
        logger.info('Приложение завершено')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass