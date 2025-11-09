# src/trading/bybit_exchange.py

from pybit.unified_trading import HTTP
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BybitExchange:
    """Клиент для торговли на Bybit (линейные фьючерсы USDT, one-way режим)"""

    TESTNET = False
    TIMEOUT = 10000
    RECV_WINDOW = 5000

    def __init__(self):
        self.http = self._init_http()
        logger.info('BybitExchange инициализирован')

    def _init_http(self) -> HTTP:
        """Инициализировать HTTP клиент"""
        return HTTP(
            api_key=config.bybit.API_KEY,
            api_secret=config.bybit.API_SECRET,
            testnet=self.TESTNET,
            timeout=self.TIMEOUT,
            recv_window=self.RECV_WINDOW
        )

    @staticmethod
    def _check_response(resp: dict, method_name: str) -> dict:
        """Проверить ответ API на ошибки"""
        if not isinstance(resp, dict):
            raise RuntimeError(f'[{method_name}] Неожиданный ответ: {resp}')

        if resp.get('retCode') != 0:
            error_msg = resp.get('retMsg', 'Unknown error')
            raise RuntimeError(f'[{method_name}] Bybit API error: {error_msg}')

        return resp.get('result') or {}

    def get_all_min_order_qty(self) -> dict[str, float]:
        """
        Получить минимальные размеры ордеров для всех линейных USDT бессрочных инструментов

        Returns:
            Dict {symbol: minOrderQty} для всех доступных активов (LinearPerpetual, quoteCoin=USDT)
        """
        try:
            results = {}
            cursor = None

            while True:
                resp = self.http.get_instruments_info(category='linear', cursor=cursor)
                result = BybitExchange._check_response(resp, 'get_instruments_info')

                instruments = result.get('list') or []
                for inst in instruments:
                    if inst.get('quoteCoin') != 'USDT':
                        continue
                    if inst.get('contractType') != 'LinearPerpetual':
                        continue

                    symbol = inst.get('symbol')
                    lot_filter = inst.get('lotSizeFilter') or {}
                    min_qty = lot_filter.get('minOrderQty')

                    if symbol and min_qty is not None:
                        results[str(symbol)] = float(min_qty)

                cursor = result.get('nextPageCursor')
                if not cursor:
                    break

            logger.debug(f'Получена информация по {len(results)} USDT perpetual инструментам')
            return results

        except Exception as e:
            logger.error(f'Ошибка получения информации по контрактам: {e}')
            raise

    def get_symbol_prices(self, symbol: str) -> dict:
        """
        Получить текущие цены символа (last, mark, index)

        Args:
            symbol: Торговая пара (например 'BTCUSDT')

        Returns:
            Dict с ключами: last, mark, index
        """
        try:
            resp = self.http.get_tickers(category='linear', symbol=symbol)
            result = BybitExchange._check_response(resp, 'get_tickers')

            tickers = result.get('list') or []
            if not tickers:
                raise RuntimeError(f'Символ {symbol} не найден')

            ticker = tickers[0]
            mark_price = float(ticker['markPrice'])
            logger.info(f'Цена {symbol}: {mark_price}')

            return {
                'last': float(ticker['lastPrice']),
                'mark': mark_price,
                'index': float(ticker['indexPrice'])
            }

        except Exception as e:
            logger.error(f'Ошибка получения цен {symbol}: {e}')
            raise

    def get_open_positions(self, symbol: str) -> list[dict]:
        """
        Получить список открытых позиций по символу

        Args:
            symbol: Торговая пара (например 'BTCUSDT')

        Returns:
            Список открытых позиций (size > 0)
        """
        try:
            resp = self.http.get_positions(category='linear', symbol=symbol)
            result = BybitExchange._check_response(resp, 'get_positions')

            positions = result.get('list') or []
            open_positions = [p for p in positions if float(p.get('size', '0')) > 0]

            logger.debug(f'Получено {len(open_positions)} открытых позиций по {symbol}')
            return open_positions

        except Exception as e:
            logger.error(f'Ошибка получения позиций {symbol}: {e}')
            raise

    def set_leverage(self, symbol: str, leverage: float) -> None:
        """
        Установить кредитное плечо для символа (one-way режим)

        Args:
            symbol: Торговая пара (например 'BTCUSDT')
            leverage: Размер плеча (например 5.0, 10.0)
        """
        try:
            resp = self.http.set_leverage(
                category='linear',
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            BybitExchange._check_response(resp, 'set_leverage')
            logger.info(f'Плечо {leverage}x для {symbol} установлено')

        except Exception as e:
            error_msg = str(e)
            if 'ErrCode: 110043' in error_msg:
                logger.info(f'Плечо {leverage}x для {symbol} уже установлено')
            else:
                logger.error(f'Ошибка установки плеча для {symbol}: {e}')
                raise

    def place_market_order(
            self,
            symbol: str,
            qty: float,
            side: str,
            tp: float,
            sl: float
    ) -> str:
        """
        Открыть рыночный ордер с Take Profit и Stop Loss

        Args:
            symbol: Торговая пара (например 'BTCUSDT')
            qty: Размер позиции в базовой валюте
            side: 'Buy' или 'Sell'
            tp: Цена Take Profit
            sl: Цена Stop Loss

        Returns:
            ID созданного ордера
        """
        try:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': side,
                'orderType': 'Market',
                'qty': str(qty),
                'stopLoss': str(sl),
                'slTriggerBy': 'MarkPrice',
                'slOrderType': 'Market',
                'takeProfit': str(tp),
                'tpTriggerBy': 'MarkPrice',
                'tpOrderType': 'Market',
                'tpslMode': 'Full'
            }

            resp = self.http.place_order(**params)
            result = BybitExchange._check_response(resp, 'place_order')

            order_id = result.get('orderId', '<unknown>')
            return order_id

        except Exception as e:
            logger.error(f'Ошибка открытия позиции {symbol}: {e}')
            raise

    def close_position(self, symbol: str, pos_side: str, qty: float) -> None:
        """
        Закрыть позицию по символу с готовым объёмом

        Args:
            symbol: Торговая пара (например 'BTCUSDT')
            pos_side: Направление открытой позиции ('Buy' или 'Sell')
            qty: Готовый, округлённый объём к закрытию
        """
        try:
            # Формируем обратный ордер
            close_side = 'Sell' if pos_side == 'Buy' else 'Buy'

            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': close_side,
                'orderType': 'Market',
                'qty': str(qty),
                'reduceOnly': 'true'
            }

            resp = self.http.place_order(**params)
            BybitExchange._check_response(resp, 'place_order')

        except Exception as e:
            logger.error(f'Ошибка закрытия позиции {symbol}: {e}')
            raise

    def disconnect(self) -> None:
        """Закрыть соединение с API"""
        if hasattr(self, 'http') and self.http:
            logger.info('BybitExchange отключен')