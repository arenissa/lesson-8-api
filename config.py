"""Загрузка настроек из переменных окружения (.env). Реальных секретов в коде нет."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    vk_group_token: str
    vk_group_id: int
    gigachat_credentials: str
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2-Pro"
    gigachat_base_url: str = "https://api.giga.chat/v1"
    sales_form_url: str = "https://zerocoder.ru/"


def get_settings() -> Settings:
    vk_token = os.getenv("VK_GROUP_TOKEN", "").strip()
    vk_group_id_raw = os.getenv("VK_GROUP_ID", "").strip()
    giga_creds = os.getenv("GIGACHAT_CREDENTIALS", "").strip()

    missing = []
    if not vk_token:
        missing.append("VK_GROUP_TOKEN")
    if not vk_group_id_raw:
        missing.append("VK_GROUP_ID")
    if not giga_creds:
        missing.append("GIGACHAT_CREDENTIALS")
    if missing:
        raise RuntimeError(
            "Не заполнены переменные окружения: " + ", ".join(missing)
            + ". Скопируй .env.example в .env и заполни их вручную. См. README.md."
        )

    try:
        vk_group_id = int(vk_group_id_raw)
    except ValueError:
        raise RuntimeError("VK_GROUP_ID должен быть числом (только цифры, без 'club' и минуса).")

    return Settings(
        vk_group_token=vk_token,
        vk_group_id=vk_group_id,
        gigachat_credentials=giga_creds,
        gigachat_scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS").strip() or "GIGACHAT_API_PERS",
        gigachat_model=os.getenv("GIGACHAT_MODEL", "GigaChat-2-Pro").strip() or "GigaChat-2-Pro",
        gigachat_base_url=os.getenv("GIGACHAT_BASE_URL", "https://api.giga.chat/v1").strip()
        or "https://api.giga.chat/v1",
        sales_form_url=os.getenv("SALES_FORM_URL", "https://zerocoder.ru/").strip()
        or "https://zerocoder.ru/",
    )
