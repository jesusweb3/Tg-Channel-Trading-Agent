# main.py

import asyncio
from src.telegram.auth import auth
from src.telegram.parser import ChannelParser
from src.ai.client import router_client
from src.trading.bybit_exchange import BybitExchange
from src.trading.strategy import TradingStrategy
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    exchange = None

    try:
        logger.info('Запуск приложения')

        # Инициализация Telegram
        client = await auth.get_client()
        await router_client.init()

        # Инициализация торговли
        exchange = BybitExchange()
        strategy = TradingStrategy(exchange)
        await strategy.init_cache()

        # Запуск парсера канала
        parser = ChannelParser(client, strategy)
        await parser.start()

        await asyncio.sleep(float('inf'))

    except asyncio.CancelledError:
        logger.info('Получен сигнал остановки')
    except Exception as e:
        logger.error(f'Ошибка: {e}', exc_info=True)
    finally:
        await auth.disconnect()
        await router_client.disconnect()
        if exchange:
            exchange.disconnect()
        logger.info('Приложение завершено')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass