"""
Модуль с unit-тестами для Telegram бота DeepSeek.

Содержит тесты основных функций бота:
- Обработка команды /start
- Обработка текстовых сообщений
- Обработка различных типов ошибок API
- Проверка вспомогательных функций

Все тесты используют mock-объекты для изоляции от внешних зависимостей.
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User
from telegram.ext import ContextTypes

# Устанавливаем фейковые переменные окружения для тестов
# Это необходимо для корректной инициализации модуля main
os.environ['TELEGRAM_TOKEN'] = 'test_token'
os.environ['DEEPSEEK_API_KEY'] = 'test_key'

import main

# Импортируем исключения OpenAI для тестирования обработки ошибок
from openai import APITimeoutError, APIError


@pytest.fixture
def mock_update():
    """Фикстура для mock Update"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.mention_html.return_value = "<a href=\"tg://user?id=12345\">TestUser</a>"
    update.message = MagicMock(spec=Message)
    update.message.reply_html = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.message.text = "Тестовое сообщение"
    return update


@pytest.fixture
def mock_context():
    """Фикстура для mock Context"""
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Тест команды /start"""
    await main.start(mock_update, mock_context)

    mock_update.message.reply_html.assert_called_once()
    call_args = mock_update.message.reply_html.call_args
    assert "Привет" in call_args[0][0]
    assert "TestUser" in call_args[0][0]


@pytest.mark.asyncio
async def test_handle_message_success(mock_update, mock_context):
    """Тест успешной обработки сообщения"""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Ответ от DeepSeek"

    with patch('main.client.chat.completions.create', return_value=mock_response) as mock_create:
        await main.handle_message(mock_update, mock_context)

        mock_create.assert_called_once()
        mock_update.message.reply_text.assert_called_once_with("Ответ от DeepSeek")


@pytest.mark.asyncio
async def test_handle_message_api_timeout(mock_update, mock_context):
    """Тест обработки таймаута API"""
    with patch('main.client.chat.completions.create', side_effect=APITimeoutError("Timeout")):
        await main.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Превышено время ожидания" in response


@pytest.mark.asyncio
async def test_handle_message_api_error_402(mock_update, mock_context):
    """Тест обработки ошибки баланса API"""
    mock_request = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 402
    error = APIError("Payment required", request=mock_request, body=None)
    error.status_code = 402

    with patch('main.client.chat.completions.create', side_effect=error):
        await main.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Недостаточно средств" in response


@pytest.mark.asyncio
async def test_handle_message_generic_api_error(mock_update, mock_context):
    """Тест обработки общей ошибки API"""
    mock_request = MagicMock()
    error = APIError("Server error", request=mock_request, body=None)
    error.status_code = 500

    with patch('main.client.chat.completions.create', side_effect=error):
        await main.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Ошибка сервера ИИ" in response


@pytest.mark.asyncio
async def test_handle_message_critical_error(mock_update, mock_context):
    """Тест обработки критической ошибки"""
    with patch('main.client.chat.completions.create', side_effect=Exception("Critical error")):
        await main.handle_message(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Внутренняя ошибка бота" in response


def test_keep_worker_alive():
    """Тест функции keep_worker_alive (базовый тест потока)"""
    # Проверяем, что функция не выбрасывает исключения при инициализации
    # Полное тестирование потока требует интеграционных тестов
    try:
        # Функция запускается в daemon потоке, поэтому просто проверяем импортируемость
        assert callable(main.keep_worker_alive)
    except Exception as e:
        pytest.fail(f"Функция keep_worker_alive не должна выбрасывать исключения: {e}")


def test_main_function_exists():
    """Тест наличия функции main"""
    assert callable(main.main)
    assert main.__name__ == "main"
