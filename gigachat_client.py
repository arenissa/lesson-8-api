"""Интеграция с GigaChat API по официальной документации (Python SDK `gigachat`).

Документация из папки проекта (GigaChat.docx):
- установка: pip install gigachat
- подключение: GigaChat(credentials=..., base_url="https://api.giga.chat/v1", scope="GIGACHAT_API_PERS")
- SDK сам получает access_token через POST /api/v2/oauth (RqUID + Basic) и шлёт
  рабочие запросы с Authorization: Bearer <токен> на /v1/chat/completions
- модель по умолчанию — GigaChat Lite; явно задаём через параметр model
"""
from pathlib import Path

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

BASE_DIR = Path(__file__).resolve().parent


def load_text_file(name: str) -> str:
    return (BASE_DIR / name).read_text(encoding="utf-8")


def build_system_prompt(sales_form_url: str) -> str:
    """Собирает системный промпт Алины + базу знаний в один системный контекст."""
    system_template = load_text_file("system_prompt.md")
    knowledge_template = load_text_file("knowledge_base.md")
    knowledge = knowledge_template.replace("{SALES_FORM_URL}", sales_form_url)
    system = system_template.replace("{SALES_FORM_URL}", sales_form_url)
    return system + "\n\n---\n\n# БАЗА ЗНАНИЙ ZEROCODER\n" + knowledge


class AlinaGigaChat:
    """Тонкая обёртка над GigaChat SDK для ответов Алины."""

    def __init__(self, credentials: str, scope: str, model: str, base_url: str, sales_form_url: str):
        self.model = model
        self.system_prompt = build_system_prompt(sales_form_url)
        # verify_ssl_certs=False — чтобы не требовать ручной установки сертификатов
        # Минцифры на Windows (см. раздел "Что подготовить заранее" в документации).
        # Для строгого режима поменяй на True и установи сертификаты.
        self._client = GigaChat(
            credentials=credentials,
            scope=scope,
            base_url=base_url,
            model=model,
            verify_ssl_certs=False,
        )

    def answer(self, user_text: str, history: list[tuple[str, str]] | None = None) -> str:
        """history — список (role, text), role: 'user' | 'assistant'. Берём последние 6 реплик."""
        messages: list[Messages] = [Messages(role=MessagesRole.SYSTEM, content=self.system_prompt)]
        for role, text in (history or [])[-6:]:
            messages.append(
                Messages(
                    role=MessagesRole.USER if role == "user" else MessagesRole.ASSISTANT,
                    content=text,
                )
            )
        messages.append(Messages(role=MessagesRole.USER, content=user_text))

        chat = Chat(messages=messages, model=self.model, temperature=0.7, max_tokens=800)
        response = self._client.chat(chat)
        reply = response.choices[0].message.content.strip()
        if not reply:
            return (
                "Спасибо за сообщение! Я не смогла сформулировать ответ, "
                "но наш менеджер обязательно поможет. Могу отправить ссылку на форму для связи?"
            )
        return reply
