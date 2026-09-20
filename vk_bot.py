"""Чат-бот сообщества ВКонтакте: отвечает на сообщения пользователей через GigaChat API.

Запуск:
    python vk_bot.py

Что нужно заранее (все значения — вручную в .env, см. README.md):
    VK_GROUP_TOKEN, VK_GROUP_ID, GIGACHAT_CREDENTIALS (+ опционально SCOPE/MODEL/URL/SALES_FORM_URL)

Как это работает:
    1. VkLongPoll слушает новые входящие сообщения сообщества (событие MESSAGE_NEW, to_me).
    2. Текст + короткая история диалога уходят в GigaChat вместе с системным промптом
       Алины и базой знаний Zerocoder (см. gigachat_client.py, system_prompt.md, knowledge_base.md).
    3. Ответ отправляется обратно через vk.messages.send.
"""
import random
import sys
import time

# Windows-консоль (cp1251/cp1252) не печатает кириллицу без настройки — включаем UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import vk_api
from vk_api.longpoll import VkEventType, VkLongPoll

from config import get_settings
from gigachat_client import AlinaGigaChat

# Память диалогов: {peer_id: [(role, text), ...]}. Хранится только пока бот запущен.
_dialogs: dict[int, list[tuple[str, str]]] = {}
MAX_HISTORY_TURNS = 6  # храним последние N пар реплик
VK_MESSAGE_LIMIT = 4096


def split_for_vk(text: str, limit: int = VK_MESSAGE_LIMIT) -> list[str]:
    """Режет длинный ответ на куски под лимит ВК, стараясь рвать по переносам строк."""
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for line in text.split("\n"):
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) > limit:
            if current:
                parts.append(current)
            while len(line) > limit:  # очень длинная строка без переносов
                parts.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts or [text[:limit]]


def main() -> None:
    settings = get_settings()
    alina = AlinaGigaChat(
        credentials=settings.gigachat_credentials,
        scope=settings.gigachat_scope,
        model=settings.gigachat_model,
        base_url=settings.gigachat_base_url,
        sales_form_url=settings.sales_form_url,
    )

    vk_session = vk_api.VkApi(token=settings.vk_group_token)
    vk = vk_session.get_api()
    group_info = vk.groups.getById(group_id=settings.vk_group_id)
    print(f"Бот Алина запущен для сообщества: {group_info[0].get('name')} (id={settings.vk_group_id})")
    print("Слушаю сообщения... (Ctrl+C для остановки)")

    longpoll = VkLongPoll(vk_session, group_id=settings.vk_group_id)

    for event in longpoll.listen():
        if event.type != VkEventType.MESSAGE_NEW or not event.to_me or not event.text:
            continue
        peer_id = event.peer_id
        user_text = event.text.strip()
        if not user_text:
            continue

        print(f"[{peer_id}]: {user_text[:120]}")
        history = _dialogs.get(peer_id, [])
        try:
            reply = alina.answer(user_text, history)
        except Exception as exc:  # не роняем longpoll из-за одной ошибки API
            print(f"Ошибка GigaChat: {exc}")
            reply = (
                "Спасибо за сообщение! Сейчас у меня технические сложности, "
                "но я уже передала вопрос менеджеру. "
                f"Оставьте заявку здесь, и мы свяжемся с вами: {settings.sales_form_url}"
            )

        history.extend([("user", user_text), ("assistant", reply)])
        _dialogs[peer_id] = history[-(MAX_HISTORY_TURNS * 2):]

        try:
            for part in split_for_vk(reply):
                vk.messages.send(peer_id=peer_id, message=part, random_id=random.randint(1, 2**31 - 1))
                time.sleep(0.4)  # пауза между кусками, чтобы не упереться в лимиты
        except Exception as exc:
            print(f"Ошибка отправки в ВК: {exc}")


if __name__ == "__main__":
    main()
