# -*- coding: utf-8 -*-
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types.bot_command import BotCommand
from datetime import datetime, time
import pytz

# Укажи токен
TOKEN = "7548603426:AAHNG1TGkBnz_cZQvEqfaFVfv1ieV-KGiTI"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище временных данных пользователей
user_temp_data = {}

# Хранилище будильников (список для каждого пользователя)
alarms = {}
time_zone = pytz.timezone("Asia/Tashkent")
active_alarm_index = {}  # Для отслеживания активного будильника каждого пользователя

# Генерация кнопок меню

def create_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Янгисидан болсин", callback_data="add_alarm")],
        [InlineKeyboardButton(text="📜 Ройхат", callback_data="list_alarms")],
        [InlineKeyboardButton(text="ℹ️ Ёрдам", callback_data="help")],
    ])

def create_repeat_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Факат эртага", callback_data="repeat_once")],
        [InlineKeyboardButton(text="Хар куни", callback_data="repeat_everyday")],
        [InlineKeyboardButton(text="Ду-се-чор-пай-жума", callback_data="repeat_weekdays")],
    ])

@dp.message(CommandStart())
async def start_command(message: types.Message):
    if message.from_user.id not in alarms:
        alarms[message.from_user.id] = []
    await message.answer(
        "Салом! Мен сизни уйготишим керак! 🕰\n\n"
        "Менюни бошкариш учун ишлатинг:",
        reply_markup=create_main_menu()
    )

@dp.callback_query(lambda callback: callback.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Менюни бошкариш учун ишлатинг:",
        reply_markup=create_main_menu()
    )

@dp.callback_query(lambda callback: callback.data == "add_alarm")
async def add_alarm(callback: CallbackQuery):
    user_temp_data[callback.from_user.id] = {"step": "time"}
    await callback.message.answer("HH:MM форматда керакли вактни киритинг:")

@dp.message(lambda message: message.from_user.id in user_temp_data and user_temp_data[message.from_user.id]["step"] == "time")
async def set_alarm_time(message: types.Message):
    try:
        alarm_time = time.fromisoformat(message.text)
        user_temp_data[message.from_user.id]["time"] = alarm_time
        user_temp_data[message.from_user.id]["step"] = "repeat"
        await message.answer("Тангланг:", reply_markup=create_repeat_buttons())
    except ValueError:
        await message.answer("❗ Ебанмисиз? Кайтадан уриниб коринг. HH:MM форматида болсин")

@dp.callback_query(lambda callback: callback.data.startswith("repeat_"))
async def set_alarm_repeat(callback: CallbackQuery):
    repeat_mode = callback.data.split("_")[1]
    alarm_time = user_temp_data[callback.from_user.id]["time"]
    if callback.from_user.id not in alarms:
        alarms[callback.from_user.id] = []
    alarms[callback.from_user.id].append({"time": alarm_time, "repeat": repeat_mode, "is_active": True, "has_rung": False})
    user_temp_data.pop(callback.from_user.id, None)
    await callback.message.answer(
        f"✅ {alarm_time.strftime('%H:%M')} вактда, ({repeat_mode}) чаладиган будильник кошилди!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Оркага", callback_data="main_menu")]
        ])
    )

@dp.callback_query(lambda callback: callback.data == "list_alarms")
async def list_alarms(callback: CallbackQuery):
    user_alarms = alarms.get(callback.from_user.id, [])
    if not user_alarms:
        await callback.message.edit_text("❗ Нихуя йок.", reply_markup=create_main_menu())
        return

    text = "🕰 Твои будильники:\n"
    buttons = []
    for i, alarm in enumerate(user_alarms):
        if alarm['has_rung']:
            status = "✅ Чалди"
        elif not alarm['is_active']:
            status = "⏹ Тохтатилди"
        else:
            status = "✅ Актив"
        text += f"{i + 1}. {alarm['time'].strftime('%H:%M')} ({alarm['repeat']}) {status}\n"
        buttons.append([InlineKeyboardButton(text=f"⚙️ Изменить {alarm['time'].strftime('%H:%M')}", callback_data=f"edit_{i}")])

    buttons.append([InlineKeyboardButton(text="❌ Хаммасига динаху", callback_data="delete_all_alarms")])
    buttons.append([InlineKeyboardButton(text="🔙 Оркага", callback_data="main_menu")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(lambda callback: callback.data == "delete_all_alarms")
async def delete_all_alarms(callback: CallbackQuery):
    if callback.from_user.id in alarms:
        alarms[callback.from_user.id] = []
    await callback.message.edit_text("❌ Хаммасини котга тикдиз.", reply_markup=create_main_menu())

@dp.message(Command("help"))
async def help_command(message: types.Message):
    text = (
        "ℹ️ Колимдан факат шу келади:\n\n"
        "➕ Меню оркали янги будильник кошиш\n"
        "📜 Меню оркали будильниклар ройхатига караш\n"
        "⏹ Актив будильникни очирмк\n\n"
        "Саволлар ва таклифлар учун: @tokushu79"
    )
    await message.answer(text)

# Проверка времени и отправка будильников
async def alarm_checker():
    while True:
        now = datetime.now(time_zone).time()
        for user_id, user_alarms in alarms.items():
            for i, alarm in enumerate(user_alarms):
                if alarm["is_active"] and now.hour == alarm['time'].hour and now.minute == alarm['time'].minute:
                    if user_id not in active_alarm_index:
                        active_alarm_index[user_id] = i
                        asyncio.create_task(send_alarm(user_id, i))
                        alarm['has_rung'] = True
        await asyncio.sleep(1)

async def send_alarm(user_id, alarm_index):
    while active_alarm_index.get(user_id) == alarm_index:
        await bot.send_message(user_id, "⏰ О ебан, уйгониш вакти келди! Чакагини очириш учун /stop жонатинг")
        await asyncio.sleep(3)

@dp.message(Command("stop"))
async def stop_alarm(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_alarm_index:
        alarm_index = active_alarm_index.pop(user_id)
        if alarm_index < len(alarms[user_id]):
            alarms[user_id][alarm_index]["is_active"] = False
        await message.answer(f"⏹ Будильник {alarm_index + 1} тохтатилди.", reply_markup=create_main_menu())
    else:
        await message.answer("❗ Сенда актив будильниклар йок.", reply_markup=create_main_menu())

# Установка команд для подсказок в Telegram
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Бот билан ишлашни бошла"),
        BotCommand(command="list", description="Ройхатни корсат"),
        BotCommand(command="help", description="Ёрдам беринг")
    ]
    await bot.set_my_commands(commands)

# Запуск бота
async def main():
    await set_commands(bot)
    asyncio.create_task(alarm_checker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
