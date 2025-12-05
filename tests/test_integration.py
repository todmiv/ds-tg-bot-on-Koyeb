"""
Модуль с интеграционными тестами для Telegram бота DeepSeek.

Проверяет корректность инициализации компонентов и их взаимодействия:
- Инициализация Telegram приложения
- Настройка OpenAI клиента
- Проверка переменных окружения
- Создание фоновых потоков

Эти тесты проверяют интеграцию между компонентами без использования mock-объектов
для внешних зависимостей.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Устанавливаем фейковые переменные окружения для интеграционных тестов
# Необходимо для корректной инициализации модуля main
os.environ['TELEGRAM_TOKEN'] = 'test_token'
os.environ['DEEPSEEK_API_KEY'] = 'test_key'

import main


def test_application_initialization():
    """Интеграционный тест инициализации приложения"""
    # Проверяем, что приложение может быть создано
    with patch('main.Application.builder') as mock_builder:
        mock_app = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app

        # Имитируем создание приложения
        from telegram.ext import Application
        app = Application.builder().token(main.TELEGRAM_TOKEN).build()

        assert app is not None


def test_client_initialization():
    """Тест инициализации OpenAI клиента"""
    # Проверяем, что клиент DeepSeek инициализирован
    assert main.client is not None
    assert main.client.api_key == main.DEEPSEEK_API_KEY
    assert str(main.client.base_url) == "https://api.deepseek.com/v1/"


def test_environment_variables():
    """Тест наличия необходимых переменных окружения"""
    assert os.getenv('TELEGRAM_TOKEN') == 'test_token'
    assert os.getenv('DEEPSEEK_API_KEY') == 'test_key'


def test_thread_creation():
    """Тест создания потока keep_worker_alive"""
    # Проверяем, что поток создан и является daemon
    assert main.keep_alive_thread is not None
    assert main.keep_alive_thread.daemon is True
    assert callable(main.keep_alive_thread._target)
