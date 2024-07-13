import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import requests

API_TOKEN = '6257427069:AAEkq5s2AvyRCu8RmBmxCW0bglsq33hmh9M'
EXCHANGE_RATE_API_KEY = '56d77fa272b930247728fcf1'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_currency_pair = {}
user_state = {}

main_currencies = [
    ("RUB", "Российский рубль"),
    ("USD", "Доллар США"),
    ("EUR", "Евро"),
    ("CNY", "Китайский юань"),
]

additional_currencies = [
    ("JPY", "Японская иена"),
    ("GBP", "Британский фунт"),
    ("CHF", "Швейцарский франк"),
    ("CAD", "Канадский доллар"),
    ("AUD", "Австралийский доллар"),
    ("HKD", "Гонконгский доллар"),
    ("SGD", "Сингапурский доллар"),
    ("SEK", "Шведская крона"),
    ("NOK", "Норвежская крона"),
    ("NZD", "Новозеландский доллар"),
    ("MXN", "Мексиканский песо"),
    ("INR", "Индийская рупия"),
    ("BRL", "Бразильский реал"),
    ("ZAR", "Южноафриканский рэнд"),
    ("TRY", "Турецкая лира"),
    ("KRW", "Южнокорейская вона"),
]

all_currencies = main_currencies + additional_currencies

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="RUB/USD"), KeyboardButton(text="RUB/EUR")],
        [KeyboardButton(text="Другая пара 🔄")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_currency_keyboard(exclude_currency=None):
    keyboard = [[KeyboardButton(text=f"{cur[0]} ({cur[1]})")] for cur in all_currencies if cur[0] != exclude_currency]
    keyboard.append([KeyboardButton(text="Назад к основным валютам ⬅️")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_currency_emoji(currency):
    emoji_map = {"RUB": "🇷🇺", "USD": "🇺🇸", "EUR": "🇪🇺", "CNY": "🇨🇳", "JPY": "🇯🇵"}
    return emoji_map.get(currency, "💱")

after_conversion_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Выбрать другую пару 🔄")],
        [KeyboardButton(text="Спасибо, больше не надо 👋")]
    ],
    resize_keyboard=True
)

@dp.message(Command(commands=['start', 'help']))
async def send_welcome(message: types.Message):
    user_state[message.from_user.id] = "choosing_main"
    await message.reply("Привет! Выбери пару валют для конвертации:", reply_markup=get_main_keyboard())

@dp.message(lambda message: message.text == "Другая пара 🔄" and user_state.get(message.from_user.id) == "choosing_main")
async def show_additional_currencies(message: types.Message):
    user_state[message.from_user.id] = "choosing_first"
    user_currency_pair[message.from_user.id] = []
    await message.reply("Выберите первую валюту из списка:", reply_markup=get_currency_keyboard())

@dp.message(lambda message: message.text == "Назад к основным валютам ⬅️")
async def back_to_main_currencies(message: types.Message):
    user_state[message.from_user.id] = "choosing_main"
    await message.reply("Выберите пару валют:", reply_markup=get_main_keyboard())

@dp.message(lambda message: user_state.get(message.from_user.id) == "choosing_first" and message.text != "Назад к основным валютам ⬅️")
async def process_first_currency(message: types.Message):
    currency = message.text.split()[0]
    user_currency_pair[message.from_user.id] = [currency]
    user_state[message.from_user.id] = "choosing_second"
    await message.reply(f"Выберите вторую валюту для конвертации из {currency}:",
                        reply_markup=get_currency_keyboard(exclude_currency=currency))

@dp.message(lambda message: user_state.get(message.from_user.id) == "choosing_second" and message.text != "Назад к основным валютам ⬅️")
async def process_second_currency(message: types.Message):
    currency = message.text.split()[0]
    user_currency_pair[message.from_user.id].append(currency)
    from_currency, to_currency = user_currency_pair[message.from_user.id]
    await message.reply(f"Введите сумму для конвертации {from_currency} в {to_currency}:")
    user_state[message.from_user.id] = "entering_amount"

@dp.message(lambda message: message.text in ["RUB/USD", "RUB/EUR"])
async def process_main_currency_pair(message: types.Message):
    from_currency, to_currency = message.text.split('/')
    user_currency_pair[message.from_user.id] = [from_currency, to_currency]
    await message.reply(f"Введите сумму для конвертации {from_currency}:")
    user_state[message.from_user.id] = "entering_amount"

@dp.message(lambda message: user_state.get(message.from_user.id) == "entering_amount" and message.text.replace('.', '', 1).isdigit())
async def process_amount(message: types.Message):
    amount = float(message.text)
    from_currency, to_currency = user_currency_pair[message.from_user.id]

    try:
        result, rate = convert_currency(from_currency, to_currency, amount)
        await message.reply(
            f"{amount} {from_currency} = {result:.2f} {to_currency}\n(Курс: 1 {from_currency} = {rate:.4f} {to_currency})",
            reply_markup=after_conversion_kb
        )
        user_state[message.from_user.id] = "converted"
    except Exception as e:
        await message.reply(f"Произошла ошибка при конвертации: {str(e)}")

@dp.message(lambda message: message.text == "Выбрать другую пару 🔄")
async def choose_another_pair(message: types.Message):
    await send_welcome(message)

@dp.message(lambda message: message.text == "Спасибо, больше не надо 👋")
async def say_goodbye(message: types.Message):
    image_url = "https://i.pinimg.com/564x/a1/e7/f7/a1e7f78b268953dd2ddec8389ceddc49.jpg"
    await message.answer_photo(photo=image_url, caption="Пожалуйста! Буду рад помочь снова 😊")

    # Опционально: сбросить состояние пользователя
    if message.from_user.id in user_state:
        del user_state[message.from_user.id]
    if message.from_user.id in user_currency_pair:
        del user_currency_pair[message.from_user.id]

def convert_currency(from_currency: str, to_currency: str, amount: float) -> tuple:
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
    response = requests.get(url)
    data = response.json()

    if data['result'] == 'success':
        conversion_result = data['conversion_result']
        conversion_rate = data['conversion_rate']
        return conversion_result, conversion_rate
    else:
        raise Exception(f"Failed to convert currency: {data['error-type']}")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
