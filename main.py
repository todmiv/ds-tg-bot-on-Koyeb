import os
import logging
import gc
import threading
import time
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI, APITimeoutError, APIError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
UPTIME_ROBOT_URL = os.getenv('UPTIME_ROBOT_URL', '')  # URL для мониторинга активности
MODEL_NAME = "deepseek-chat"
REQUEST_TIMEOUT = 30  # Таймаут запросов к DeepSeek

# Проверка обязательных переменных
if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    logger.error("Отсутствуют обязательные переменные окружения!")
    exit(1)

# Инициализация клиента DeepSeek
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# Функция для периодического пинга
def keep_worker_alive():
    """Периодически отправляет запросы для поддержания активности воркера"""
    while True:
        try:
            # Пинг Telegram API
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe", timeout=10)
            
            # Пинг UptimeRobot
            if UPTIME_ROBOT_URL:
                requests.get(UPTIME_ROBOT_URL, timeout=5)
                
            logger.info("Пинг отправлен для поддержания активности")
        except Exception as e:
            logger.error(f"Ошибка при отправке пинга: {str(e)}")
        
        # Очистка памяти
        gc.collect()
        
        # Ожидание 10 минут
        time.sleep(600)

# Запуск потока для поддержания активности
keep_alive_thread = threading.Thread(target=keep_worker_alive, daemon=True)
keep_alive_thread.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет {user.mention_html()}! Я бот с искусственным интеллектом DeepSeek. Просто напиши мне сообщение, и я постараюсь помочь!",
        reply_markup=None
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    try:
        user_message = update.message.text
        logger.info(f"Сообщение от {update.effective_user.id}: {user_message[:50]}...")
        
        # Запрос к DeepSeek API с таймаутом
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "Ты полезный AI-ассистент DeepSeek-R1. Отвечай на русском."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                stream=False,
                timeout=REQUEST_TIMEOUT
            )
            ai_response = response.choices[0].message.content
        except APITimeoutError:
            logger.warning("Таймаут запроса к DeepSeek API")
            ai_response = "⏳ Превышено время ожидания ответа. Попробуйте более короткий запрос."
        except APIError as e:
            if e.status_code == 402:
                logger.error("Ошибка баланса DeepSeek")
                ai_response = "⚠️ Недостаточно средств на API-аккаунте!"
            else:
                logger.error(f"Ошибка API: {str(e)}")
                ai_response = "⚠️ Ошибка сервера ИИ. Попробуйте позже."
        
        # Отправка ответа
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        try:
            await update.message.reply_text("⚠️ Внутренняя ошибка бота. Администратор уведомлен.")
        except:
            pass  # Избегаем повторных ошибок
        
    finally:
        # Оптимизация памяти после обработки
        gc.collect()

def main():
    """Запуск бота"""
    # Создаем приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе")
    app.run_polling()

if __name__ == "__main__":
    main()
