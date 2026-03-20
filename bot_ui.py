from __future__ import annotations

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from logic import format_welcome


(
    ROUTE_NUMBER,
    ROUTE_NAME,
    CLASS_TS,
    ROUTE_TYPE,
    MODEL_TS,
    FUEL_TYPE,
    MILEAGE,
    QTY_MAIN,
    QTY_RES,
    CAPACITY,
    PRICE,
    LIFETIME,
    CONTRACT_PERIOD,
    FARE,
    SUBSIDY,
    CLIMATE,
) = range(16)


CB_TEMPLATE = "template_nmck"

CB_CLASS_PREFIX = "class_"
CB_ROUTE_TYPE_PREFIX = "route_type_"
CB_FUEL_PREFIX = "fuel_"
CB_CLIMATE_PREFIX = "climate_"


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Универсальный шаблон расчета НМЦК", callback_data=CB_TEMPLATE)],
        ]
    )


def build_class_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Особо малый", callback_data=CB_CLASS_PREFIX + "osobo_malyi")],
            [InlineKeyboardButton("Малый", callback_data=CB_CLASS_PREFIX + "malyi")],
            [InlineKeyboardButton("Средний", callback_data=CB_CLASS_PREFIX + "srednii")],
            [InlineKeyboardButton("Большой", callback_data=CB_CLASS_PREFIX + "bolshoi")],
            [InlineKeyboardButton("Особо большой", callback_data=CB_CLASS_PREFIX + "osobo_bolshoi")],
        ]
    )


def build_route_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Городской", callback_data=CB_ROUTE_TYPE_PREFIX + "city")],
            [InlineKeyboardButton("Пригородный", callback_data=CB_ROUTE_TYPE_PREFIX + "suburban")],
            [InlineKeyboardButton("Межмуниципальный", callback_data=CB_ROUTE_TYPE_PREFIX + "intermunicipal")],
        ]
    )


def build_fuel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Бензин", callback_data=CB_FUEL_PREFIX + "petrol")],
            [InlineKeyboardButton("Дизель", callback_data=CB_FUEL_PREFIX + "diesel")],
            [InlineKeyboardButton("Газ", callback_data=CB_FUEL_PREFIX + "gas")],
            [InlineKeyboardButton("Электрический", callback_data=CB_FUEL_PREFIX + "electric")],
        ]
    )


def build_climate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Слабая", callback_data=CB_CLIMATE_PREFIX + "weak")],
            [InlineKeyboardButton("Умеренная", callback_data=CB_CLIMATE_PREFIX + "moderate")],
            [InlineKeyboardButton("Сильная", callback_data=CB_CLIMATE_PREFIX + "strong")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = format_welcome(user.first_name if user else None)
    await update.message.reply_text(text, reply_markup=build_start_keyboard())


async def start_template_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data["form"] = {}
    await q.edit_message_text("Введите номер маршрута:")
    return ROUTE_NUMBER


def _only_letters_and_digits(value: str) -> bool:
    return value.isalnum()


def _contains_digits(value: str) -> bool:
    return any(ch.isdigit() for ch in value)


def _contains_letters(value: str) -> bool:
    return any(ch.isalpha() for ch in value)


async def handle_route_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ROUTE_NUMBER
    text = update.message.text.strip()
    if not text or not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: номер маршрута должен содержать только цифры, без букв и символов.</i>\n"
            "Введите номер маршрута ещё раз:"
        )
        return ROUTE_NUMBER

    context.user_data.setdefault("form", {})["route_number"] = text
    await update.message.reply_text(
        "Введите наименование маршрута:\n"
        "<i>Можно использовать буквы и символы, но без цифр.</i>",
        parse_mode="HTML",
    )
    return ROUTE_NAME


async def handle_route_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ROUTE_NAME
    text = update.message.text.strip()
    if not text or _contains_digits(text):
        await update.message.reply_text(
            "<i>Ошибка: наименование маршрута не должно содержать цифр.</i>\n"
            "Введите наименование маршрута ещё раз:",
            parse_mode="HTML",
        )
        return ROUTE_NAME

    context.user_data.setdefault("form", {})["route_name"] = text
    await update.message.reply_text("Класс ТС:", reply_markup=build_class_keyboard())
    return CLASS_TS


async def handle_class_ts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    mapping = {
        CB_CLASS_PREFIX + "osobo_malyi": "Особо малый",
        CB_CLASS_PREFIX + "malyi": "Малый",
        CB_CLASS_PREFIX + "srednii": "Средний",
        CB_CLASS_PREFIX + "bolshoi": "Большой",
        CB_CLASS_PREFIX + "osobo_bolshoi": "Особо большой",
    }
    value = mapping.get(data)
    if not value:
        await q.answer("Неизвестный класс ТС.", show_alert=True)
        return CLASS_TS

    context.user_data.setdefault("form", {})["class_ts"] = value
    await q.edit_message_text("Тип маршрута:", reply_markup=build_route_type_keyboard())
    return ROUTE_TYPE


async def handle_route_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    mapping = {
        CB_ROUTE_TYPE_PREFIX + "city": "Городской",
        CB_ROUTE_TYPE_PREFIX + "suburban": "Пригородный",
        CB_ROUTE_TYPE_PREFIX + "intermunicipal": "Межмуниципальный",
    }
    value = mapping.get(data)
    if not value:
        await q.answer("Неизвестный тип маршрута.", show_alert=True)
        return ROUTE_TYPE

    context.user_data.setdefault("form", {})["route_type"] = value
    await q.edit_message_text(
        "Введите модель ТС:\n<i>Марка и модель автобуса (или эквивалент).</i>",
    )
    return MODEL_TS


async def handle_model_ts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return MODEL_TS
    text = update.message.text.strip()
    if not text or not _only_letters_and_digits(text.replace(" ", "")):
        await update.message.reply_text(
            "<i>Ошибка: модель ТС может содержать только буквы, цифры и пробелы, без символов.</i>\n"
            "Введите модель ТС ещё раз:"
        )
        return MODEL_TS

    context.user_data.setdefault("form", {})["model_ts"] = text
    await update.message.reply_text("Тип топлива:", reply_markup=build_fuel_keyboard())
    return FUEL_TYPE


async def handle_fuel_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    mapping = {
        CB_FUEL_PREFIX + "petrol": "Бензин",
        CB_FUEL_PREFIX + "diesel": "Дизель",
        CB_FUEL_PREFIX + "gas": "Газ",
        CB_FUEL_PREFIX + "electric": "Электрический",
    }
    value = mapping.get(data)
    if not value:
        await q.answer("Неизвестный тип топлива.", show_alert=True)
        return FUEL_TYPE

    context.user_data.setdefault("form", {})["fuel_type"] = value
    await q.edit_message_text("Введите пробег по контракту:")
    return MILEAGE


async def handle_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return MILEAGE
    text = update.message.text.strip()
    if not text or _contains_letters(text):
        await update.message.reply_text(
            "<i>Ошибка: пробег по контракту может содержать только цифры и символы, без букв.</i>\n"
            "Введите пробег по контракту ещё раз:"
        )
        return MILEAGE

    context.user_data.setdefault("form", {})["mileage"] = text
    await update.message.reply_text(
        "Введите количества ТС (основное):\n"
        "<i>Максимальное количество ТС на маршруте</i>"
    )
    return QTY_MAIN


async def handle_qty_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return QTY_MAIN
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: количество ТС (основное) должно быть только цифрами.</i>\n"
            "Введите количество ТС (основное) ещё раз:"
        )
        return QTY_MAIN

    context.user_data.setdefault("form", {})["qty_main"] = text
    await update.message.reply_text("Введите количество ТС (резерв):")
    return QTY_RES


async def handle_qty_res(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return QTY_RES
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: количество ТС (резерв) должно быть только цифрами.</i>\n"
            "Введите количество ТС (резерв) ещё раз:"
        )
        return QTY_RES

    context.user_data.setdefault("form", {})["qty_res"] = text
    await update.message.reply_text("Введите вместимость ТС:")
    return CAPACITY


async def handle_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return CAPACITY
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: вместимость ТС должна быть только цифрами.</i>\n"
            "Введите вместимость ТС ещё раз:"
        )
        return CAPACITY

    context.user_data.setdefault("form", {})["capacity"] = text
    await update.message.reply_text("Введите цену ТС:")
    return PRICE


async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return PRICE
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: цена ТС должна быть только цифрами.</i>\n"
            "Введите цену ТС ещё раз:"
        )
        return PRICE

    context.user_data.setdefault("form", {})["price"] = text
    await update.message.reply_text("Введите срок службы ТС (лет):")
    return LIFETIME


async def handle_lifetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return LIFETIME
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: срок службы ТС должен быть только цифрами.</i>\n"
            "Введите срок службы ТС (лет) ещё раз:"
        )
        return LIFETIME

    context.user_data.setdefault("form", {})["lifetime"] = text
    await update.message.reply_text("Введите период контракта:")
    return CONTRACT_PERIOD


async def handle_contract_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return CONTRACT_PERIOD
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: период контракта должен быть только цифрами.</i>\n"
            "Введите период контракта ещё раз:"
        )
        return CONTRACT_PERIOD

    context.user_data.setdefault("form", {})["contract_period"] = text
    await update.message.reply_text("Введите планируемую плату за проезд:")
    return FARE


async def handle_fare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return FARE
    text = update.message.text.strip()
    if not text or _contains_letters(text):
        await update.message.reply_text(
            "<i>Ошибка: планируемая плата за проезд может содержать только цифры и символы, без букв.</i>\n"
            "Введите плату за проезд ещё раз:"
        )
        return FARE

    context.user_data.setdefault("form", {})["fare"] = text
    await update.message.reply_text("Введите размер субсидий:")
    return SUBSIDY


async def handle_subsidy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return SUBSIDY
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "<i>Ошибка: размер субсидий должен быть только цифрами.</i>\n"
            "Введите размер субсидий ещё раз:"
        )
        return SUBSIDY

    context.user_data.setdefault("form", {})["subsidy"] = text
    await update.message.reply_text("Климатическая зона:", reply_markup=build_climate_keyboard())
    return CLIMATE


async def handle_climate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    mapping = {
        CB_CLIMATE_PREFIX + "weak": "Слабая",
        CB_CLIMATE_PREFIX + "moderate": "Умеренная",
        CB_CLIMATE_PREFIX + "strong": "Сильная",
    }
    value = mapping.get(data)
    if not value:
        await q.answer("Неизвестная климатическая зона.", show_alert=True)
        return CLIMATE

    form = context.user_data.setdefault("form", {})
    form["climate_zone"] = value

    try:
        qty_main = int(form.get("qty_main", "0"))
        qty_res = int(form.get("qty_res", "0"))
        total_ts = qty_main + qty_res
    except ValueError:
        total_ts = "?"

    summary_lines = [
        "Результаты, которые вы ввели:",
        f"- Номер маршрута: {form.get('route_number', '-')}",
        f"- Наименование маршрута: {form.get('route_name', '-')}",
        f"- Класс ТС: {form.get('class_ts', '-')}",
        f"- Тип маршрута: {form.get('route_type', '-')}",
        f"- Модель ТС: {form.get('model_ts', '-')}",
        f"- Тип топлива: {form.get('fuel_type', '-')}",
        f"- Пробег по контракту: {form.get('mileage', '-')}",
        f"- Количество ТС (основное): {form.get('qty_main', '-')}",
        f"- Количество ТС (резерв): {form.get('qty_res', '-')}",
        f"- Вместимость ТС: {form.get('capacity', '-')}",
        f"- Цена ТС: {form.get('price', '-')}",
        f"- Срок службы ТС (лет): {form.get('lifetime', '-')}",
        f"- Период контракта: {form.get('contract_period', '-')}",
        f"- Планируемая плата за проезд: {form.get('fare', '-')}",
        f"- Размер субсидий: {form.get('subsidy', '-')}",
        f"- Климатическая зона: {form.get('climate_zone', '-')}",
        "",
        f"Количество ТС ИТОГО: {total_ts}",
        "Скоро тут будут расчёты :)",
    ]

    await q.edit_message_text("\n".join(summary_lines))
    return ConversationHandler.END


async def webapp_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    if not webapp_url:
        await update.message.reply_text(
            "Не задано `WEBAPP_URL`. Укажите URL мини‑приложения (например, https://ваш-сервер/).",
            parse_mode="Markdown",
        )
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Открыть расчет НМЦК",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        ]
    )
    user = update.effective_user
    text = format_welcome(user.first_name if user else None)
    await update.message.reply_text(text, reply_markup=keyboard)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Missing BOT_TOKEN env var. Example: export BOT_TOKEN='123:ABC' && python bot_ui.py")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", webapp_start))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

