"""Shared, versioned demonstration scoring for company observations."""
import math
from commerce_signals import COMMERCE_BONUS, commerce_metadata, commerce_reason

SCORING_VERSION = "company-rules-v2"
MAX_RAW_SCORE = 65
RISK_BANDS = {"medium": 30, "high": 71}


def risk_tier(score):
    if score is None:
        return "unknown"
    return "low" if score < RISK_BANDS["medium"] else "medium" if score < RISK_BANDS["high"] else "high"


def normalize_company(data, require_name=False):
    if not isinstance(data, dict):
        raise ValueError("Ожидается объект с данными компании.")
    company = {}
    for field in ("name", "social_media", "region", "sector", "phone"):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"Поле {field} должно быть текстом.")
        company[field] = value.strip() or None if value is not None else None
    if require_name and not company["name"]:
        raise ValueError("Укажите название компании.")

    def number(field, required=True):
        value = data.get(field)
        if value is None or value == "":
            if not required:
                return None
            raise ValueError(f"Поле {field} обязательно.")
        if isinstance(value, bool):
            raise ValueError(f"Поле {field} должно быть числом.")
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"Поле {field} должно быть числом.") from None
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Поле {field} должно быть конечным неотрицательным числом.")
        return value

    company["revenue"] = number("revenue")
    employees = number("employees")
    if not employees.is_integer() or employees > 9007199254740991:
        raise ValueError("Количество сотрудников должно быть целым числом от 0 до 9007199254740991.")
    company["employees"] = int(employees)
    percent = number("tax_percent", False)
    paid = number("tax_paid", False)
    if paid is not None and company["revenue"] > 0:
        derived = paid / company["revenue"] * 100
        if percent is not None and not math.isclose(percent, derived, rel_tol=0, abs_tol=1e-6):
            raise ValueError("tax_percent не совпадает с tax_paid / revenue × 100.")
        percent = derived
    if percent is None and company["revenue"] > 0:
        raise ValueError("Укажите tax_percent или tax_paid за тот же период, что и revenue.")
    if percent is not None and (not math.isfinite(percent) or not 0 <= percent <= 100):
        raise ValueError("Налоговая доля должна быть от 0 до 100 %.")
    company["tax_percent"] = round(percent, 8) if percent is not None else None
    return company


def analyze_company(company):
    company = normalize_company(company)
    # Демонстрационные правила: пороги не являются налоговыми нормативами.
    signals = []
    score = 0

    def flag(label, reason, weight):
        nonlocal score
        signals.append({"column": label, "count": 1, "threshold": reason, "raw_weight": weight})
        score += weight

    if company["revenue"] > 0 and company["tax_percent"] is not None and company["tax_percent"] < 3:
        flag("Налог, %", "Положительная выручка при налоговой доле ниже 3 %.",
             30 if company["tax_percent"] < 1 else 15)
    if company["revenue"] > 0 and company["employees"] == 0:
        flag("Количество сотрудников", "Есть выручка, но сотрудники не указаны (0).", 20)
    if company["revenue"] == 0 and company["employees"] > 0:
        flag("Доход / выручка", "При наличии сотрудников указана нулевая выручка.", 20)
    if company["revenue"] == 0 and (company["social_media"] or "").casefold() == "высокая":
        flag("Активность в соцсетях", "Высокая активность при нулевой выручке.", 12)
    commerce = commerce_metadata(company.get("social_media"), company.get("revenue"))
    if commerce["commerce_signal"]:
        flag("Активность в соцсетях", commerce_reason(commerce["commerce_keywords"]), COMMERCE_BONUS)
    statistics = {}
    for field, label in (("revenue", "Доход / выручка"),
                         ("tax_percent", "Налог, %"),
                         ("employees", "Количество сотрудников")):
        statistics[label] = dict.fromkeys(
            ("mean", "median", "min", "max", "sum"), company[field]
        )
    normalized_score = min(100, round(score * 100 / MAX_RAW_SCORE))
    return {
        **commerce,
        "rows": 1, "columns": 8,
        "numeric_columns": ["revenue", "tax_percent", "employees"],
        "missing_values": sum(company.get(field) is None for field in ("social_media", "region", "sector", "phone")),
        "duplicates": 0, "anomalies": signals, "statistics": statistics,
        "raw_score": score, "scoring_version": SCORING_VERSION,
        "risk_score": normalized_score,
        "risk_tier": risk_tier(normalized_score),
        "note": "Единые демонстрационные правила v2: сумма баллов / 65 × 100. Пропуски, дубликаты и ±3σ не увеличивают риск. Это не вероятность нарушения; отрасль и налоговый режим не учтены.",
    }

