# src/trading/signal_parser.py

import re
from dataclasses import dataclass
from typing import Union
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EntrySignal:
    """Сигнал входа в позицию"""
    asset: str
    direction: str
    leverage: float
    tp: float
    sl: float


@dataclass
class ExitSignal:
    """Сигнал закрытия позиции"""
    asset: str
    exit_type: str
    percentage: float | None = None


def parse(ai_response: str) -> Union[EntrySignal, ExitSignal, None]:
    """
    Парсить ответ ИИ и возвернуть типизированный сигнал

    Args:
        ai_response: Ответ от ИИ классификатора

    Returns:
        EntrySignal, ExitSignal или None если не удалось распарсить
    """
    response = ai_response.strip()

    if response == "NOISE":
        return None

    entry_signal = _parse_entry(response)
    if entry_signal:
        return entry_signal

    exit_signal = _parse_exit(response)
    if exit_signal:
        return exit_signal

    logger.warning(f'Не удалось распарсить сигнал: {response}')
    return None


def _parse_entry(response: str) -> Union[EntrySignal, None]:
    """Парсить сигнал входа: ASSET Long/Short Leverage:5x TP:0.32 SL:0.11"""
    pattern = r'(\w+)\s+(Long|Short)\s+Leverage:(\S+)\s+TP:(\S+)\s+SL:(\S+)'
    match = re.match(pattern, response)

    if not match:
        return None

    asset, direction, leverage_str, tp_str, sl_str = match.groups()

    try:
        leverage = _parse_number(leverage_str, "Leverage")
        tp = _parse_number(tp_str, "TP")
        sl = _parse_number(sl_str, "SL")

        if leverage is None or tp is None or sl is None:
            return None

        return EntrySignal(
            asset=asset,
            direction=direction,
            leverage=leverage,
            tp=tp,
            sl=sl
        )
    except Exception as e:
        logger.error(f'Ошибка при парсинге entry сигнала: {e}')
        return None


def _parse_exit(response: str) -> Union[ExitSignal, None]:
    """Парсить сигнал выхода: ASSET close {%|all}"""
    pattern = r'(\w+)\s+close\s+(.+?)$'
    match = re.match(pattern, response)

    if not match:
        return None

    asset, exit_value = match.groups()
    exit_value = exit_value.strip()

    if exit_value == "all":
        return ExitSignal(asset=asset, exit_type="all")

    percentage_match = re.match(r'(\d+(?:\.\d+)?)%', exit_value)
    if percentage_match:
        try:
            percentage = float(percentage_match.group(1))
            if not (0 < percentage <= 100):
                logger.warning(f'Процент выхода вне диапазона (0, 100]: {percentage}')
                return None
            return ExitSignal(asset=asset, exit_type="percentage", percentage=percentage)
        except ValueError:
            logger.error(f'Не удалось преобразовать процент в число: {exit_value}')
            return None

    logger.warning(f'Неверный формат exit сигнала: {exit_value}')
    return None


def _parse_number(value_str: str, param_name: str) -> Union[float, None]:
    """
    Парсить число из строки, удаляя 'x' если есть

    Args:
        value_str: Строка с числом (например '5x' или '0.32')
        param_name: Имя параметра для логирования

    Returns:
        float или None если не удалось распарсить
    """
    try:
        cleaned = value_str.rstrip('x')
        return float(cleaned)
    except ValueError:
        logger.error(f'{param_name} не является числом: {value_str}')
        return None