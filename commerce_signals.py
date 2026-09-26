import math


COMMERCE_KEYWORDS = ["цена", "заказ", "доставка", "скидка", "опт", "продажа", "акция", "в наличии"]
# Демонстрационный порог в единицах входных данных, без предположения о валюте.
LOW_REVENUE_THRESHOLD = 1000
COMMERCE_BONUS = 15


def detect_commerce_signals(text: str) -> list[str]:
    normalized = text.casefold() if isinstance(text, str) else ""
    return [keyword for keyword in COMMERCE_KEYWORDS if keyword in normalized]


def commerce_metadata(text, revenue) -> dict:
    keywords = detect_commerce_signals(text)
    try:
        amount = float(revenue)
    except (TypeError, ValueError, OverflowError):
        amount = math.nan
    low_revenue = not math.isfinite(amount) or amount <= LOW_REVENUE_THRESHOLD
    return {"commerce_signal": bool(keywords) and low_revenue, "commerce_keywords": keywords}


def commerce_reason(keywords) -> str:
    return (
        "Обнаружены признаки торговой активности в соцсетях при низком/нулевом заявленном доходе: "
        + ", ".join(keywords)
    )
