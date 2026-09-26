import os
import json
import uuid
import math
from io import BytesIO
import pandas as pd

from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from google import genai
from database import init_db, insert_company, get_company, get_all_companies, update_company_score
from database import find_linked_companies
from report_export import build_pdf, build_xlsx, build_csv
from commerce_signals import COMMERCE_KEYWORDS, COMMERCE_BONUS, commerce_metadata, commerce_reason

load_dotenv()

app = Flask(__name__)
init_db()
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def load_dataframe(path):
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def analyze_data(path):
    df = load_dataframe(path)

    rows, columns = df.shape
    numeric = df.select_dtypes(include="number").columns.tolist()

    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())

    statistics = {}
    for col in numeric:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) == 0:
            continue
        statistics[col] = {
            "mean": round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "sum": round(float(s.sum()), 2)
        }

    anomalies = []
    for col in numeric:
        s = pd.to_numeric(df[col], errors="coerce")
        mean, std = s.mean(), s.std()
        if pd.isna(std) or std == 0:
            continue
        mask = (s > mean + 3 * std) | (s < mean - 3 * std)
        count = int(mask.sum())
        if count:
            anomalies.append({
                "column": col,
                "count": count,
                "threshold": f"±3σ от среднего"
            })

    # Простая демонстрационная оценка риска.
    # Это НЕ утверждение о незаконной деятельности.
    risk_score = min(
        100,
        int(
            min(len(anomalies) * 12, 60)
            + min(duplicates / max(rows, 1) * 20, 20)
            + min(missing / max(rows * max(columns, 1), 1) * 100, 20)
        )
    )

    commerce_rows = []
    if "social_media" in df.columns:
        for row_number, (_, row) in enumerate(df.iterrows(), 1):
            metadata = commerce_metadata(row.get("social_media"), row.get("revenue"))
            if metadata["commerce_signal"]:
                commerce_rows.append({"row": row_number, **metadata})
    commerce_keywords = [keyword for keyword in COMMERCE_KEYWORDS
                         if any(keyword in row["commerce_keywords"] for row in commerce_rows)]
    if commerce_rows:
        risk_score = min(100, risk_score + COMMERCE_BONUS)
        anomalies.append({"column": "Активность в соцсетях", "count": len(commerce_rows),
                          "threshold": commerce_reason(commerce_keywords)})

    return {
        "commerce_signal": bool(commerce_rows), "commerce_keywords": commerce_keywords,
        "commerce_rows": commerce_rows,
        "rows": rows,
        "columns": columns,
        "numeric_columns": numeric,
        "missing_values": missing,
        "duplicates": duplicates,
        "anomalies": anomalies,
        "statistics": statistics,
        "risk_score": risk_score,
        "note": "Risk Score — демонстрационный аналитический индикатор, а не доказательство нарушения."
    }


REPORT_SCHEMA = {
    "type": "OBJECT",
    "required": ["company_name", "revenue", "employees", "social_media", "score", "recommendation"],
    "properties": {
        "company_name": {"type": "STRING", "nullable": True},
        "revenue": {"type": "NUMBER", "nullable": True},
        "employees": {"type": "INTEGER", "nullable": True},
        "social_media": {"type": "STRING", "nullable": True},
        "score": {"type": "INTEGER", "minimum": 0, "maximum": 100},
        "recommendation": {
            "type": "OBJECT",
            "required": ["needs_inspection", "reason"],
            "properties": {
                "needs_inspection": {"type": "BOOLEAN"},
                "reason": {"type": "STRING"},
            },
        },
    },
}


def normalize_report_input(analysis, company=None):
    company = company or {}
    facts = {}
    for field in ("name", "revenue", "employees", "social_media",
                  "tax_percent", "region", "sector"):
        value = company.get(field)
        if isinstance(value, str):
            value = value.strip() or None
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            value = value if math.isfinite(value) else None
        else:
            value = None
        if value is not None and field in ("revenue", "employees", "tax_percent"):
            try:
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    value = None
                elif field == "employees":
                    value = int(value) if value.is_integer() else None
            except (ValueError, OverflowError):
                value = None
        elif value is not None:
            value = str(value)
        if value is not None:
            facts[field] = value
    return {"company": facts, "analysis": analysis}


def generate_ai_report(data):
    analysis = data["analysis"]
    signal_reason = commerce_reason(analysis.get("commerce_keywords", [])) if analysis.get("commerce_signal") else ""

    def fallback(message):
        if not signal_reason:
            return message
        company = data["company"]
        return {
            "company_name": company.get("name"), "revenue": company.get("revenue"),
            "employees": company.get("employees"), "social_media": company.get("social_media"),
            "score": analysis["risk_score"],
            "recommendation": {"needs_inspection": True,
                               "reason": signal_reason + ". Нужна сверка человеком; это локальный сигнал, отчёт Gemini недоступен и нарушение не установлено."},
        }

    if not client:
        return fallback("Gemini API не настроен. Локальный анализ выполнен; рекомендация о проверке недоступна.")

    prompt = """

Ты — бизнес-аналитик.

На вход ты получаешь НЕ исходный CSV-файл и НЕ сырые данные.

Все вычисления уже выполнены заранее с помощью Pandas.

Тебе передаются готовые показатели и результаты анализа для одной конкретной компании.

Твоя задача — НЕ пересчитывать данные, а интерпретировать готовые цифры понятным человеческим языком.

Используй только переданные данные.

Не придумывай отсутствующие показатели.

Не утверждай, что компания нарушает закон, скрывает налоги или занимается незаконной деятельностью. Если показатели необычные, говори, что они требуют дополнительной проверки.

---

## Что может приходить на вход

Например:

Компания: TechNova LLC
Регион: Tashkent
Отрасль: IT
Доход: 1 250 000 000 UZS
Количество сотрудников: 28
Налоговая ставка: 12%

Доход на сотрудника: 44 642 857 UZS

Средний доход по отрасли: 900 000 000 UZS
Отклонение от среднего дохода отрасли: +38.9%

Средний доход на сотрудника по отрасли: 31 000 000 UZS
Отклонение: +44%

Среднее количество сотрудников по отрасли: 35
Отклонение: -20%

Средняя налоговая ставка по отрасли: 12%

Risk Score: 57
Уровень риска: Средний

Обнаруженные Pandas-флаги:
- income_above_sector_average
- employees_below_sector_average
- income_per_employee_high

---

## Твоя задача

На основании этих готовых данных сформируй отдельный анализ компании.

Не выполняй новые математические вычисления, если необходимые значения уже переданы.

Не спорь с результатами Pandas и не меняй переданный Risk Score.

Если Pandas передал Risk Score = 57, используй именно 57.

Если какие-либо показатели не переданы — просто не анализируй их.

---

# Формат ответа

## [Название компании]

### Общая оценка

Кратко, в 2–4 предложениях, объясни состояние компании.

Напиши:
- насколько показатели выглядят обычными или необычными;
- есть ли существенные отклонения;
- что в первую очередь заслуживает внимания.

Пиши простым языком.

---

### Основные показатели

Кратко перечисли наиболее важные переданные данные:

- Регион
- Отрасль
- Доход
- Количество сотрудников
- Налоговая ставка
- Доход на сотрудника

Если какого-либо показателя нет во входных данных — не придумывай его.

---

### Что выглядит нормально

Объясни положительные или обычные показатели.

Например:

"Налоговая ставка компании соответствует среднему значению по отрасли, поэтому по этому показателю существенных отклонений не наблюдается."

или:

"Доход компании находится близко к среднему значению для предприятий этой отрасли."

---

### На что стоит обратить внимание

Интерпретируй отклонения и флаги, рассчитанные Pandas.

Например, если передано:

Доход выше среднего по отрасли: +38.9%

Количество сотрудников ниже среднего: -20%

Доход на сотрудника выше среднего: +44%

Объясни:

"Компания получает примерно на 39% больше дохода, чем средняя компания данной отрасли, при этом количество сотрудников примерно на 20% ниже среднего. В результате доход на одного сотрудника заметно выше отраслевого уровня. Это может говорить о высокой эффективности бизнеса, автоматизации или специфике бизнес-модели, но при проведении риск-анализа такой показатель стоит дополнительно проверить."

Всегда допускай несколько возможных объяснений.

Не интерпретируй аномалию автоматически как нарушение.

---

### Возможные риски

Используй только выявленные Pandas-флаги и переданные показатели.

Для каждого важного отклонения объясни:

1. Что обнаружено.
2. Почему это интересно для анализа.
3. Какое нормальное объяснение может существовать.
4. Что можно проверить дополнительно.

Например:

**Высокий доход на сотрудника**

Компания показывает существенно более высокий доход на одного сотрудника по сравнению со средним уровнем отрасли.

Это может быть связано с высокой производительностью, автоматизацией, цифровой бизнес-моделью или небольшим количеством высокооплачиваемых специалистов.

Однако для более точной оценки рекомендуется сопоставить показатель с банковским оборотом, фондом оплаты труда и динамикой количества сотрудников.

---

### Risk Score

Покажи переданное значение:

**Risk Score: 57/100 — Средний риск**

Затем объясни человеческим языком, какие показатели повлияли на такую оценку.

НЕ пересчитывай Risk Score самостоятельно.

НЕ повышай и НЕ понижай его.

---

### Рекомендации

Предложи 2–5 конкретных действий для дополнительной проверки.

Выбирай рекомендации исходя из обнаруженных отклонений.

Например:

- сравнить заявленный доход с банковским оборотом;
- изучить динамику дохода за последние 12 месяцев;
- проверить динамику количества сотрудников;
- сравнить фонд оплаты труда с количеством сотрудников;
- сравнить компанию с предприятиями аналогичного размера;
- проверить налоговые платежи за несколько периодов;
- изучить резкие изменения дохода;
- сопоставить показатели с отраслевыми нормами.

Не рекомендуй проверки, которые вообще не связаны с переданными данными.

---

### Итог для пользователя

Закончи коротким понятным выводом.

Например:

"В целом компания показывает хорошие финансовые показатели, однако её доход на одного сотрудника значительно превышает отраслевой уровень. Сам по себе этот показатель не говорит о нарушениях, но в сочетании с меньшим количеством сотрудников он заслуживает дополнительной проверки. Основное внимание стоит уделить банковскому обороту, фонду оплаты труда и динамике сотрудников."

---

# Очень важные правила

1. Pandas отвечает за вычисления.
2. Ты отвечаешь только за интерпретацию.
3. Не пересчитывай показатели без необходимости.
4. Не изменяй Risk Score.
5. Не придумывай отсутствующие данные.
6. Не называй компанию нарушителем закона.
7. Аномалия ≠ нарушение.
8. Всегда объясняй результаты простым языком.
9. Избегай слишком сложной финансовой терминологии.
10. Анализируй только одну компанию из текущего входного объекта.
11. Если система последовательно отправляет 10 компаний, дай отдельный анализ каждой компании.
12. Не объединяй несколько компаний в один общий ответ, если они передаются отдельно.
13. Если показатель сильно отличается от нормы, объясни не только риск, но и возможное нормальное бизнес-объяснение.
14. Если данные выглядят нормальными, прямо скажи, что значительных отклонений не обнаружено.

"""
# Верни ровно шесть полей в следующем порядке:
# 1. company_name — название компании из company.name, иначе null.
# 2. revenue — доход из company.revenue, иначе null.
# 3. employees — количество сотрудников из company.employees, иначе null.
# 4. social_media — активность в социальных сетях из company.social_media, иначе null.
# 5. score — скопируй analysis.risk_score, целое число от 0 до 100.
# 6. recommendation — объект с needs_inspection (строго true или false) и reason.
# Ты — AI-аналитик экономической активности.

# Твоя задача — анализировать предоставленные
# экономические данные и выявлять статистические
# несоответствия и потенциальные аномалии.

# НЕ утверждай, что компания нарушает закон.
# НЕ называй компанию нарушителем.
# Формируй только аналитические сигналы.

# Проанализируй:

# - заявленную выручку;
# - объём платежей;
# - количество сотрудников;
# - рекламную активность;
# - активность в социальных сетях;
# - отрасль;
# - регион.

# Определи:

# 1. anomaly_score от 0 до 100;
# 2. уровень аномальности;
# 3. основные факторы;
# 4. какие показатели расходятся;
# 5. краткое аналитическое заключение;
# 6. рекомендации для дальнейшего анализа.
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=json.dumps(data, ensure_ascii=False),
            config={
                "system_instruction": prompt,
                "response_mime_type": "application/json",
                "response_schema": REPORT_SCHEMA,
            },
        )
        raw = response.text or ""
    except Exception:
        return fallback("Не удалось получить отчёт Gemini. Локальный анализ выполнен; рекомендация о проверке недоступна.")

    try:
        text = raw.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        report = json.loads(text)
        if not isinstance(report, dict) or set(report) != set(REPORT_SCHEMA["required"]):
            raise ValueError("Неверная структура отчёта.")
        recommendation = report["recommendation"]
        if (not isinstance(recommendation, dict)
                or set(recommendation) != {"needs_inspection", "reason"}
                or type(recommendation["needs_inspection"]) is not bool
                or not isinstance(recommendation["reason"], str)
                or not recommendation["reason"].strip()):
            raise ValueError("Неверная структура рекомендации.")
        if type(report["score"]) is not int or not 0 <= report["score"] <= 100:
            raise ValueError("Неверная оценка.")
        # Факты и оценка берутся из входных данных, чтобы модель не меняла их.
        company = data["company"]
        if signal_reason:
            recommendation["needs_inspection"] = True
            if signal_reason not in recommendation["reason"]:
                recommendation["reason"] = signal_reason + ". Требуется сверка дохода человеком; при пропуске доход неизвестен, сигнал не доказывает нарушение."
        return {
            "company_name": company.get("name"),
            "revenue": company.get("revenue"),
            "employees": company.get("employees"),
            "social_media": company.get("social_media"),
            "score": data["analysis"]["risk_score"],
            "recommendation": {
                "needs_inspection": recommendation["needs_inspection"],
                "reason": recommendation["reason"].strip(),
            },
        }
    except (ValueError, TypeError, KeyError, IndexError):
        return fallback(raw or "Gemini вернул пустой ответ. Рекомендация о проверке недоступна.")


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/contacts")
def contacts():
    return render_template("contacts.html")


@app.get("/about")
def about():
    return render_template("about.html")


@app.get("/api/regions/summary")
def regions_summary():
    try:
        groups = {}
        for company in get_all_companies():
            region = " ".join((company.get("region") or "").split()) or "Регион не указан"
            group = groups.setdefault(region.casefold(), {
                "region": region, "company_count": 0,
                "scores": [], "high_risk_count": 0,
            })
            group["company_count"] += 1
            score = company.get("risk_score")
            if type(score) in (int, float) and math.isfinite(score) and 0 <= score <= 100:
                group["scores"].append(score)
                group["high_risk_count"] += int(score >= 71)
        regions = []
        for group in sorted(groups.values(), key=lambda item: item["region"].casefold()):
            scores = group.pop("scores")
            group["average_risk_score"] = round(sum(scores) / len(scores), 2) if scores else None
            regions.append(group)
        response = jsonify({"success": True, "regions": regions})
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception:
        return jsonify({"success": False, "error": "Не удалось загрузить сводку по регионам."}), 500


def validate_manual_entry(data):
    if not isinstance(data, dict):
        raise ValueError("Ожидается объект с данными компании в формате JSON.")
    company = {}
    for field, label in (
        ("name", "Название компании"), ("social_media", "Активность в соцсетях"),
        ("region", "Регион"), ("sector", "Отрасль"),
        ("phone", "Телефон"),
    ):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"Поле «{label}» должно быть текстом.")
        company[field] = value.strip() or None if value is not None else None
    if not company["name"]:
        raise ValueError("Укажите название компании.")
    for field, label in (
        ("revenue", "Доход / выручка"), ("tax_percent", "Налог, %"),
        ("employees", "Количество сотрудников"),
    ):
        value = data.get(field)
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError(f"Поле «{label}» обязательно и должно быть числом.")
        try:
            number = float(value)
        except (ValueError, OverflowError):
            raise ValueError(f"Поле «{label}» должно быть числом.") from None
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"Поле «{label}» должно быть конечным неотрицательным числом.")
        if field == "tax_percent" and number > 100:
            raise ValueError("Налог должен быть в диапазоне от 0 до 100 %.")
        if field == "employees":
            if not number.is_integer() or number > 9007199254740991:
                raise ValueError("Количество сотрудников должно быть целым числом от 0 до 9007199254740991.")
            number = int(number)
        company[field] = number
    company["source"] = "manual"
    return company


def analyze_company(company):
    # Демонстрационные правила: пороги не являются налоговыми нормативами.
    signals = []
    score = 0

    def flag(label, reason, weight):
        nonlocal score
        signals.append({"column": label, "count": 1, "threshold": reason})
        score += weight

    if company["revenue"] > 0 and company["tax_percent"] < 3:
        flag("Налог, %", "Положительная выручка при налоговой доле ниже 3 %.",
             30 if company["tax_percent"] < 1 else 15)
    if company["revenue"] > 0 and company["employees"] == 0:
        flag("Количество сотрудников", "Есть выручка, но сотрудники не указаны (0).", 20)
    if company["revenue"] == 0 and company["employees"] > 0:
        flag("Доход / выручка", "При наличии сотрудников указана нулевая выручка.", 20)
    if company["revenue"] == 0 and company["social_media"] == "высокая":
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
    return {
        **commerce,
        "rows": 1, "columns": 8,
        "numeric_columns": ["revenue", "tax_percent", "employees"],
        "missing_values": sum(company.get(field) is None for field in ("social_media", "region", "sector", "phone")),
        "duplicates": 0, "anomalies": signals, "statistics": statistics,
        "risk_score": min(100, score),
        "note": "Демонстрационная оценка одной компании; сигналы не доказывают нарушение. Пороги не учитывают отрасль и налоговый режим.",
    }


@app.post("/api/manual-entry")
def manual_entry():
    try:
        company = validate_manual_entry(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400

    try:
        analysis = analyze_company(company)
        company.update({key: analysis[key] for key in ("commerce_signal", "commerce_keywords")})
        company_id = insert_company(company)
        report = generate_ai_report(normalize_report_input(analysis, company))
        recommendation = json.dumps(report["recommendation"], ensure_ascii=False) if isinstance(report, dict) else report
        update_company_score(company_id, analysis["risk_score"], recommendation)
        return jsonify({
            "success": True, "company": get_company(company_id),
            "risk_score": analysis["risk_score"], "ai_report": report,
            "analysis": analysis,
        })
    except Exception:
        return jsonify({"success": False, "error": "Не удалось завершить сохранение и анализ компании."}), 500


@app.post("/api/analyze")
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "Файл не найден"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Файл не выбран"}), 400

    name = file.filename.lower()
    if not name.endswith((".csv", ".xlsx", ".xls")):
        return jsonify({"error": "Поддерживаются CSV и Excel"}), 400

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(path)

    try:
        analysis = analyze_data(path)
        # Только единственная строка может описывать одну компанию.
        frame = load_dataframe(path)
        company = frame.iloc[0].to_dict() if len(frame) == 1 else None
        normalized = normalize_report_input(analysis, company)
        report = generate_ai_report(normalized)
        company_id = insert_company({**normalized["company"], "source": "upload",
                                     "commerce_signal": analysis["commerce_signal"],
                                     "commerce_keywords": analysis["commerce_keywords"]})
        recommendation = json.dumps(report["recommendation"], ensure_ascii=False) if isinstance(report, dict) else report
        update_company_score(company_id, analysis["risk_score"], recommendation)
        return jsonify({
            "success": True,
            "company": get_company(company_id),
            "analysis": analysis,
            "ai_report": report
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@app.get("/api/report/<int:company_id>/download")
def download_report(company_id):
    formats = {
        "pdf": (build_pdf, "application/pdf"),
        "xlsx": (build_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "csv": (build_csv, "text/csv; charset=utf-8"),
    }
    file_format = request.args.get("format", "pdf")
    if file_format not in formats:
        return jsonify({"error": "Неверный формат. Выберите PDF, Excel или CSV."}), 400
    try:
        company = get_company(company_id)
        if company is None:
            return jsonify({"error": "Запись с указанным номером не найдена."}), 404
        raw = company.get("recommendation")
        try:
            recommendation = json.loads(raw) if raw else None
        except (ValueError, TypeError):
            recommendation = None
        if (not isinstance(recommendation, dict)
                or type(recommendation.get("needs_inspection")) is not bool
                or not isinstance(recommendation.get("reason"), str)):
            recommendation = {"needs_inspection": None, "reason": raw or "Рекомендация недоступна."}
        record = {
            "company_name": company["name"], "revenue": company["revenue"],
            "employees": company["employees"], "social_media": company["social_media"],
            "score": company["risk_score"], "recommendation": recommendation,
        }
        builder, mimetype = formats[file_format]
        content = builder(record)
        response = send_file(
            BytesIO(content), mimetype=mimetype, as_attachment=True,
            download_name=f"otchet_{company_id}.{file_format}", max_age=0,
        )
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception:
        return jsonify({"error": "Не удалось сформировать отчёт. Проверьте данные и ключ шифрования."}), 500


@app.get("/api/graph")
def company_graph():
    try:
        nodes = {}
        edges = []
        for pair in find_linked_companies():
            for endpoint in ("source", "target"):
                node = pair[endpoint]
                nodes[node["id"]] = node
            edges.append({
                "source": pair["source"]["id"],
                "target": pair["target"]["id"],
                "reason": pair["reason"],
            })
        response = jsonify({"nodes": list(nodes.values()), "edges": edges})
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception:
        return jsonify({"error": "Не удалось загрузить граф связей."}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5500, debug=True)
