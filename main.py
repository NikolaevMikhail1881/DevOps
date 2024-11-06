import configparser
import telebot
from telebot import types
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import User
import requests

# Настройка конфигурации
config = configparser.ConfigParser()
config.read("config.ini")
API_TOKEN = config["telegram"]["api_token"]
WEATHER_API_KEY = config["weather"]["api_key"]

# Инициализация бота и подключение к БД
bot = telebot.TeleBot(API_TOKEN)
try:
    alembic = configparser.ConfigParser()
    alembic.read("alembic.ini")
    DATABASE_URL = alembic["alembic"]["sqlalchemy.url"]
    Session = sessionmaker(bind=create_engine(DATABASE_URL))
except Exception as e:
    print("Ошибка подключения к БД:", e)
    exit()

# Команды бота
commands = [
    types.BotCommand("start", "Начало работы с ботом"),
    types.BotCommand("current_weather", "Получить текущую погоду"),
    types.BotCommand("forecast", "Прогноз на несколько дней"),
    types.BotCommand("set_location", "Установить локацию"),
    types.BotCommand("alerts", "Получить уведомления о погодных изменениях"),
]
bot.set_my_commands(commands)

# Вспомогательные функции
def get_weather(city):
    """Получение данных о погоде из API"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_forecast(city):
    """Получение прогноза на несколько дней"""
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(
        message.chat.id, "Привет! Я WeatherNow - бот для получения информации о погоде."
    )

@bot.message_handler(commands=["current_weather"])
def current_weather(message):
    session = Session()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user and user.city:
        weather_data = get_weather(user.city)
        if weather_data:
            bot.send_message(
                message.chat.id,
                f"Погода в {user.city}:\nТемпература: {weather_data['main']['temp']}°C\n"
                f"Ощущается как: {weather_data['main']['feels_like']}°C\n"
                f"Погодные условия: {weather_data['weather'][0]['description']}"
            )
        else:
            bot.send_message(message.chat.id, "Не удалось получить данные о погоде.")
    else:
        bot.send_message(message.chat.id, "Сначала установите свой город командой /set_location.")
    session.close()

@bot.message_handler(commands=["forecast"])
def weather_forecast(message):
    session = Session()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user and user.city:
        forecast_data = get_forecast(user.city)
        if forecast_data:
            forecast_message = f"Прогноз погоды на несколько дней в {user.city}:\n"
            for item in forecast_data["list"][:5]:  # Получаем данные только на несколько дней
                date = datetime.fromtimestamp(item["dt"]).strftime("%d-%m %H:%M")
                temp = item["main"]["temp"]
                description = item["weather"][0]["description"]
                forecast_message += f"{date}: {temp}°C, {description}\n"
            bot.send_message(message.chat.id, forecast_message)
        else:
            bot.send_message(message.chat.id, "Не удалось получить прогноз.")
    else:
        bot.send_message(message.chat.id, "Сначала установите свой город командой /set_location.")
    session.close()

@bot.message_handler(commands=["set_location"])
def set_location(message):
    bot.send_message(message.chat.id, "Введите название вашего города:")
    bot.register_next_step_handler(message, process_city)

def process_city(message):
    city = message.text
    weather_data = get_weather(city)
    if weather_data:
        session = Session()
        user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            user = User(telegram_id=message.from_user.id, city=city)
            session.add(user)
        else:
            user.city = city
        session.commit()
        session.close()
        bot.send_message(message.chat.id, f"Ваш город установлен как {city}.")
    else:
        bot.send_message(message.chat.id, "Не удалось определить город, попробуйте снова.")

@bot.message_handler(commands=["alerts"])
def weather_alerts(message):
    session = Session()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user and user.city:
        weather_data = get_weather(user.city)
        if weather_data and weather_data.get("alerts"):
            alert_message = f"Предупреждения для {user.city}:\n"
            for alert in weather_data["alerts"]:
                alert_message += f"{alert['event']}: {alert['description']}\n"
            bot.send_message(message.chat.id, alert_message)
        else:
            bot.send_message(message.chat.id, "Сейчас нет погодных предупреждений.")
    else:
        bot.send_message(message.chat.id, "Сначала установите свой город командой /set_location.")
    session.close()

if __name__ == "__main__":
    bot.polling()
