# src/trading/strategy.py

from typing import Union
from src.trading.signal_parser import EntrySignal, ExitSignal
from src.trading.bybit_exchange import BybitExchange
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TradingStrategy:
    """Стратегия обработки торговых сигналов"""

    SYMBOL_SUFFIX = 'USDT'

    def __init__(self, exchange: BybitExchange):
        self.exchange = exchange
        self.min_order_qty_cache: dict[str, float] = {}

    async def init_cache(self) -> None:
        """Инициализировать кеш минимальных объёмов при старте приложения"""
        try:
            self.min_order_qty_cache = self.exchange.get_all_min_order_qty()
            logger.info(f'Кеш инициализирован: {len(self.min_order_qty_cache)} активов')
        except Exception as e:
            logger.error(f'Ошибка инициализации кеша: {e}')
            raise

    async def process_signal(self, signal: Union[EntrySignal, ExitSignal, None]) -> None:
        """
        Обработать полученный сигнал

        Args:
            signal: Распарсенный сигнал (EntrySignal, ExitSignal или None)
        """
        if signal is None:
            return

        try:
            if isinstance(signal, EntrySignal):
                await self._process_entry(signal)
            elif isinstance(signal, ExitSignal):
                await self._process_exit(signal)
        except Exception as e:
            logger.error(f'Ошибка обработки сигнала: {e}', exc_info=True)

    async def _process_entry(self, signal: EntrySignal) -> None:
        """Обработка сигнала входа в позицию"""
        symbol_full = f'{signal.asset}{self.SYMBOL_SUFFIX}'

        # 1. Проверить наличие актива на бирже
        if symbol_full not in self.min_order_qty_cache:
            logger.warning(f'Актив {symbol_full} не найден на бирже, сигнал пропущен')
            return

        min_order_qty = self.min_order_qty_cache[symbol_full]

        logger.info(f'Обработка entry сигнала: {signal.asset} {signal.direction} {signal.leverage}x')

        # 2. Установить кредитное плечо
        try:
            self.exchange.set_leverage(symbol_full, signal.leverage)
        except Exception as e:
            logger.error(f'Ошибка установки плеча: {e}')
            return

        # 3. Получить текущую цену
        try:
            prices = self.exchange.get_symbol_prices(symbol_full)
            current_price = prices['last']
        except Exception as e:
            logger.error(f'Ошибка получения цены {symbol_full}: {e}')
            return

        # 4. Рассчитать объём позиции
        qty = TradingStrategy._calculate_qty(current_price, signal.leverage)
        if qty is None:
            return

        # 5. Округлить по правилам биржи
        qty_rounded = TradingStrategy._round_quantity(qty, min_order_qty)
        logger.info(f'Рассчитан объём: {qty:.2f}, округлено: {qty_rounded}')

        # 6. Определить направление
        side = 'Buy' if signal.direction == 'Long' else 'Sell'

        # 7. Открыть позицию
        try:
            order_id = self.exchange.place_market_order(
                symbol=symbol_full,
                qty=qty_rounded,
                side=side,
                tp=signal.tp,
                sl=signal.sl
            )
            logger.info(
                f'Позиция открыта: {side} {qty_rounded} {symbol_full} @ TP:{signal.tp} SL:{signal.sl} (orderId: {order_id})'
            )
        except Exception as e:
            logger.error(f'Ошибка открытия позиции {symbol_full}: {e}')

    async def _process_exit(self, signal: ExitSignal) -> None:
        """Обработка сигнала выхода из позиции"""
        symbol_full = f'{signal.asset}{self.SYMBOL_SUFFIX}'

        # Проверить наличие актива в кеше
        if symbol_full not in self.min_order_qty_cache:
            logger.warning(f'Актив {symbol_full} не найден на бирже, сигнал пропущен')
            return

        min_order_qty = self.min_order_qty_cache[symbol_full]

        # 1. Проверить наличие открытой позиции
        try:
            positions = self.exchange.get_open_positions(symbol_full)
        except Exception as e:
            logger.error(f'Ошибка получения позиций {symbol_full}: {e}')
            return

        if not positions:
            logger.info(f'Нет открытой позиции по {symbol_full}, сигнал пропущен')
            return

        pos_size = float(positions[0]['size'])
        pos_side = positions[0]['side']
        logger.info(f'Обработка exit сигнала: {signal.asset} close {signal.exit_type}')

        # 2. Рассчитать объём к закрытию
        if signal.exit_type == 'all':
            qty_to_close = pos_size
            percent = 100.0
        elif signal.exit_type == 'percentage' and signal.percentage is not None:
            qty_to_close = pos_size * (signal.percentage / 100.0)
            percent = signal.percentage
        else:
            logger.warning(f'Неверный exit type: {signal.exit_type}')
            return

        # 3. Округлить по правилам биржи
        qty_rounded = TradingStrategy._round_quantity(qty_to_close, min_order_qty)

        # 4. Закрыть позицию
        try:
            self.exchange.close_position(symbol_full, pos_side, qty_rounded)
            logger.info(f'Позиция закрыта: {percent}% от {pos_size} {symbol_full} ({qty_rounded} контрактов)')
        except Exception as e:
            logger.error(f'Ошибка закрытия позиции {symbol_full}: {e}')

    @staticmethod
    def _calculate_qty(price: float, leverage: float) -> Union[float, None]:
        """
        Рассчитать объём позиции

        Формула:
        margin = balance * amount / 100
        position_volume = margin * leverage
        qty = position_volume / price

        Args:
            price: Текущая цена актива
            leverage: Кредитное плечо

        Returns:
            Объём позиции или None при ошибке
        """
        try:
            margin = config.BALANCE * config.AMOUNT / 100
            position_volume = margin * leverage
            qty = position_volume / price
            return qty
        except Exception as e:
            logger.error(f'Ошибка расчёта объёма: {e}')
            return None

    @staticmethod
    def _round_quantity(qty: float, min_order_qty: float) -> float:
        """
        Округлить объём по правилам биржи

        Определяем количество знаков после запятой из min_order_qty
        и округляем до этого же количества знаков.

        Args:
            qty: Расчётный объём
            min_order_qty: Минимальный объём заказа (определяет точность)

        Returns:
            Округлённый объём
        """
        min_qty_str = str(min_order_qty)

        if '.' in min_qty_str:
            decimal_places = len(min_qty_str.split('.')[1])
        else:
            decimal_places = 0

        qty_rounded = round(qty, decimal_places)
        return qty_rounded