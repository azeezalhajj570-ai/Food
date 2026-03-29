from food_ordering import db
from food_ordering.models import AppSetting


def get_setting(key, default=None):
    setting = AppSetting.query.filter_by(key=key).first()
    if setting is None or setting.value in (None, ""):
        return default
    return setting.value


def set_setting(key, value):
    setting = AppSetting.query.filter_by(key=key).first()
    if setting is None:
        setting = AppSetting(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    return setting


def get_ai_settings(config):
    return {
        "gemini_api_key": get_setting("gemini_api_key", config.get("GEMINI_API_KEY", "")) or "",
        "gemini_model": get_setting("gemini_model", config.get("GEMINI_MODEL", "gemini-2.5-flash")) or "gemini-2.5-flash",
        "recommendation_prompt": get_setting("recommendation_prompt", _default_prompt()) or _default_prompt(),
    }


def _default_prompt():
    return (
        "Rank food recommendations for this ordering platform using user history, cart context, "
        "popular combinations, and frequently bought together behavior. Favor practical upsells and "
        "relevant meal pairings over random variety."
    )
