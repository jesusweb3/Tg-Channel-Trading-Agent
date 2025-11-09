# src/ai/client.py

import httpx
from src.utils.config import config
from src.utils.logger import get_logger
from src.ai.prompts import PromptManager

logger = get_logger(__name__)


class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"
    TIMEOUT = 30

    def __init__(self):
        self.client: httpx.AsyncClient | None = None

    async def init(self) -> None:
        """Инициализировать клиент при старте приложения"""
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
        logger.info('OpenRouter клиент инициализирован')

    async def classify(self, prompt: str) -> str:
        """
        Отправить промт на классификацию и получить ответ
        """
        if self.client is None:
            raise RuntimeError('OpenRouter клиент не инициализирован. Вызовите init() перед использованием.')

        headers = {
            "Authorization": f"Bearer {config.openrouter.API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.openrouter.MODEL,
            "messages": [
                {"role": "system", "content": PromptManager.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 100
        }

        try:
            response = await self.client.post(f"{self.BASE_URL}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            answer = data['choices'][0]['message']['content'].strip()

            logger.info(f'Получен ответ от модели: {answer}')
            return answer

        except httpx.HTTPStatusError as e:
            logger.error(f'HTTP ошибка {e.response.status_code}: {e.response.text}')
            raise
        except (KeyError, IndexError) as e:
            logger.error(f'Ошибка парсинга ответа: {e}')
            raise
        except Exception as e:
            logger.error(f'Ошибка при запросе к OpenRouter: {e}')
            raise

    async def disconnect(self) -> None:
        """Закрыть соединение с OpenRouter"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info('OpenRouter клиент отключен')


router_client = OpenRouterClient()