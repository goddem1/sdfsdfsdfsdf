from __future__ import annotations


def format_welcome(name: str | None) -> str:
    who = name.strip() if name else ""
    who = who if who else "друг"
    return (
        f"Привет, {who}!\n\n"
        "Я бот-калькулятор. Пока что я умею только интерфейс (кнопки/приветствие).\n"
        "Дальше добавим сбор входных данных и расчёты по формулам."
    )

