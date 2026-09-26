import io
import csv
import json
import os
import re
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet
from google.genai import types
from openpyxl import load_workbook

from report_export import build_csv, build_pdf, build_xlsx, DISCLAIMER
from commerce_signals import detect_commerce_signals, commerce_metadata


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = TemporaryDirectory()
        cls.environment = patch.dict(os.environ, {
            "ENCRYPTION_KEY": Fernet.generate_key().decode(), "GEMINI_API_KEY": "",
        })
        cls.environment.start()
        import database
        cls.database = database
        cls.db_path = patch.object(database, "DB_PATH", Path(cls.directory.name) / "test.db")
        cls.db_path.start()
        import app
        cls.module = app

    @classmethod
    def tearDownClass(cls):
        cls.db_path.stop()
        cls.environment.stop()
        cls.directory.cleanup()

    def setUp(self):
        self.company = {
            "name": "Компания", "revenue": 1000, "tax_percent": 0.5,
            "employees": 0, "social_media": "высокая", "region": None, "sector": None,
        }
        self.data = self.module.normalize_report_input(
            self.module.analyze_company(self.company), self.company
        )
        self.report = {
            "company_name": "Компания", "revenue": 1000,
            "employees": 0, "social_media": "высокая", "score": 50,
            "recommendation": {"needs_inspection": True, "reason": "Нужна сверка показателей."},
        }

    def generate(self, text, data=None):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text=text)
        with patch.object(self.module, "client", client):
            result = self.module.generate_ai_report(data or self.data)
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(types.GenerateContentConfig(**config).response_mime_type, "application/json")
        return result

    def test_structured_report_and_order(self):
        result = self.generate(json.dumps(self.report))
        self.assertEqual(result, self.report)
        self.assertEqual(list(result), list(self.report))

    def test_facts_and_score_cannot_be_invented(self):
        invented = {**self.report, "company_name": "Выдумано", "revenue": 999, "score": 99}
        self.assertEqual(self.generate(json.dumps(invented)), self.report)
        aggregate = self.module.normalize_report_input({"risk_score": 0, "rows": 10})
        result = self.generate(json.dumps(invented), aggregate)
        self.assertIsNone(result["company_name"])
        self.assertIsNone(result["revenue"])
        self.assertEqual(result["score"], 0)

    def test_fenced_json(self):
        self.assertEqual(self.generate("```json\n" + json.dumps(self.report) + "\n```"), self.report)

    def test_invalid_json_and_structure_fall_back(self):
        for text in ("<script>текст</script>", "null", "[]", "{}", "```",
                     json.dumps({**self.report, "score": 101}),
                     json.dumps({**self.report, "recommendation": {"needs_inspection": "false", "reason": "Нет"}})):
            with self.subTest(text=text):
                self.assertEqual(self.generate(text), text)

    def test_missing_key_empty_response_and_api_failure(self):
        with patch.object(self.module, "client", None):
            self.assertIn("не настроен", self.module.generate_ai_report(self.data))
        self.assertIn("пустой ответ", self.generate(""))
        client = Mock()
        client.models.generate_content.side_effect = RuntimeError("Секретные сведения")
        with patch.object(self.module, "client", client):
            result = self.module.generate_ai_report(self.data)
        self.assertIn("Не удалось", result)
        self.assertNotIn("Секретные сведения", result)

    def test_manual_route_persists_recommendation(self):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text=json.dumps(self.report))
        with patch.object(self.module, "client", client):
            response = self.module.app.test_client().post("/api/manual-entry", json=self.company)
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result["ai_report"], self.report)
        saved = self.database.get_company(result["company"]["id"])
        self.assertEqual(json.loads(saved["recommendation"]), self.report["recommendation"])
        with sqlite3.connect(self.database.DB_PATH) as connection:
            name = connection.execute("SELECT name FROM companies WHERE id = ?", (saved["id"],)).fetchone()[0]
        self.assertNotEqual(name, self.company["name"])

    def test_uploads_use_normalized_input(self):
        for csv, expected in (
            ("name,revenue,employees,social_media\nКомпания,1000,0,высокая\n", "Компания"),
            ("name,revenue\nПервая,1000\nВторая,2000\n", None),
        ):
            with self.subTest(csv=csv), patch.object(self.module, "generate_ai_report", return_value=self.report) as generate:
                response = self.module.app.test_client().post("/api/analyze", data={
                    "file": (io.BytesIO(csv.encode()), "sample.csv"),
                })
                self.assertEqual(response.status_code, 200)
                normalized = generate.call_args.args[0]
                self.assertEqual(set(normalized), {"company", "analysis"})
                self.assertEqual(normalized["company"].get("name"), expected)

    def test_export_builders(self):
        csv_bytes = build_csv(self.report)
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(rows), 8)
        self.assertEqual([row[0] for row in rows[:6]], [
            "Название компании", "Доход", "Количество сотрудников",
            "Активность в социальных сетях", "Оценка риска", "Рекомендация",
        ])
        self.assertEqual(rows[0][1], "Компания")
        self.assertEqual(rows[2][1], "0")
        self.assertIn("Проверка нужна: Да", rows[5][1])
        self.assertEqual(rows[6][1], DISCLAIMER)
        self.assertIn("UTC", rows[7][1])
        workbook = load_workbook(io.BytesIO(build_xlsx(self.report)))
        self.assertEqual(len(workbook.worksheets), 1)
        self.assertEqual(workbook.active["B1"].value, "Компания")
        self.assertEqual(workbook.active["B2"].value, 1000)
        self.assertEqual(workbook.active["B3"].value, 0)
        workbook.close()
        long_report = {**self.report, "recommendation": {
            "needs_inspection": False, "reason": "Текст проверки. " * 1000,
        }}
        for report in (self.report, long_report):
            pdf = build_pdf(report)
            self.assertTrue(pdf.startswith(b"%PDF-"))
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 1)
            self.assertIn(b"/FontFile2", pdf)

    def test_commerce_keywords_and_threshold(self):
        self.assertEqual(detect_commerce_signals("ЦЕНА, заказ, ЗАКАЗ; доставка; в наличии"),
                         ["цена", "заказ", "доставка", "в наличии"])
        self.assertEqual(detect_commerce_signals("высокая"), [])
        for revenue in (0, None, "", 999, 1000):
            self.assertTrue(commerce_metadata("Доставка", revenue)["commerce_signal"])
        self.assertFalse(commerce_metadata("Доставка", 1001)["commerce_signal"])
        self.assertFalse(commerce_metadata("", 0)["commerce_signal"])

    def test_manual_commerce_persistence_and_report(self):
        company = {**self.company, "social_media": "Скидка, доставка, заказ"}
        baseline = self.module.analyze_company(self.company)["risk_score"]
        with patch.object(self.module, "client", None):
            response = self.module.app.test_client().post("/api/manual-entry", json=company)
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertTrue(result["company"]["commerce_signal"])
        self.assertEqual(result["company"]["commerce_keywords"], ["заказ", "доставка", "скидка"])
        self.assertEqual(result["risk_score"], baseline + 15)
        self.assertIn("Обнаружены признаки торговой активности", result["ai_report"]["recommendation"]["reason"])
        analysis = self.module.analyze_company(company)
        data = self.module.normalize_report_input(analysis, company)
        report = self.generate(json.dumps(self.report), data)
        self.assertTrue(report["recommendation"]["needs_inspection"])
        self.assertIn("заказ, доставка, скидка", report["recommendation"]["reason"])
        self.assertEqual(list(report), list(self.report))

    def test_upload_commerce_matches_each_rows_revenue(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "commerce.csv"
            path.write_text("social_media,revenue\nДоставка,1001\nПривет,0\n", encoding="utf-8")
            self.assertFalse(self.module.analyze_data(path.as_posix())["commerce_signal"])
            path.write_text("social_media,revenue\nДоставка,\nЗаказ,1000\n", encoding="utf-8")
            result = self.module.analyze_data(path.as_posix())
            self.assertTrue(result["commerce_signal"])
            self.assertEqual(result["commerce_keywords"], ["заказ", "доставка"])
            self.assertEqual(len(result["commerce_rows"]), 2)
            self.assertEqual(result["risk_score"], 35)
            path.write_text("social_media\nДоставка\n", encoding="utf-8")
            self.assertTrue(self.module.analyze_data(path.as_posix())["commerce_signal"])

    def test_phone_migration(self):
        with TemporaryDirectory() as directory, patch.object(self.database, "DB_PATH", Path(directory) / "legacy.db"):
            with sqlite3.connect(self.database.DB_PATH) as connection:
                connection.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT)")
                connection.execute("INSERT INTO companies (id, name) VALUES (1, 'сохранено')")
            self.database.init_db()
            self.database.init_db()
            with sqlite3.connect(self.database.DB_PATH) as connection:
                self.assertEqual(connection.execute("SELECT name, phone FROM companies").fetchone(), ("сохранено", None))
                self.assertEqual([r[1] for r in connection.execute("PRAGMA table_info(companies)")].count("phone"), 1)

    def test_encrypted_links_and_graph(self):
        with TemporaryDirectory() as directory, patch.object(self.database, "DB_PATH", Path(directory) / "links.db"):
            self.database.init_db()
            first = self.database.insert_company({"name": "Первая", "phone": " +99890 ", "social_media": " Профиль ", "source": "manual"})
            second = self.database.insert_company({"name": "Вторая", "phone": "+99890", "social_media": "профиль", "source": "manual"})
            self.database.insert_company({"name": "Без связи", "phone": " ", "social_media": "", "source": "manual"})
            self.database.insert_company({"source": "manual"})
            self.assertEqual(self.database.get_company(first)["phone"], " +99890 ")
            with sqlite3.connect(self.database.DB_PATH) as connection:
                encrypted = connection.execute("SELECT phone FROM companies WHERE id = ?", (first,)).fetchone()[0]
                self.assertNotIn("+99890", encrypted)
            pairs = self.database.find_linked_companies()
            self.assertEqual(len(pairs), 2)
            self.assertEqual({p["reason"] for p in pairs}, {"same phone", "same social media"})
            result = self.module.app.test_client().get("/api/graph")
            self.assertEqual(result.status_code, 200)
            self.assertEqual({n["id"] for n in result.json["nodes"]}, {first, second})
            self.assertEqual(len(result.json["edges"]), 2)
            self.assertNotIn("phone", result.json["nodes"][0])
            self.assertNotIn("+99890", result.get_data(as_text=True))

    def test_manual_phone_and_empty_graph(self):
        client = self.module.app.test_client()
        with patch.object(self.module, "client", None):
            result = client.post("/api/manual-entry", json={**self.company, "phone": " +998 90 "})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["company"]["phone"], "+998 90")
        self.assertEqual(client.post("/api/manual-entry", json={**self.company, "phone": 123}).status_code, 400)
        with patch.object(self.module, "find_linked_companies", return_value=[]):
            self.assertEqual(client.get("/api/graph").json, {"nodes": [], "edges": []})
        with patch.object(self.module, "find_linked_companies", side_effect=ValueError("Секрет")):
            self.assertEqual(client.get("/api/graph").status_code, 500)

    def test_regions_summary(self):
        companies = [
            {"region": " Ташкент ", "risk_score": 70},
            {"region": "ташкент", "risk_score": 71},
            {"region": "Ташкент", "risk_score": None},
            {"region": "Самарканд", "risk_score": 0},
            {"region": None, "risk_score": 100},
            {"region": "  ", "risk_score": None},
            {"region": "Бухара", "risk_score": None},
        ]
        with patch.object(self.module, "get_all_companies", return_value=companies):
            response = self.module.app.test_client().get("/api/regions/summary")
        self.assertEqual(response.status_code, 200)
        regions = {row["region"]: row for row in response.json["regions"]}
        self.assertEqual(regions["Ташкент"], {
            "region": "Ташкент", "company_count": 3,
            "average_risk_score": 70.5, "high_risk_count": 1,
        })
        self.assertEqual(regions["Самарканд"]["average_risk_score"], 0)
        self.assertEqual(regions["Регион не указан"]["company_count"], 2)
        self.assertIsNone(regions["Бухара"]["average_risk_score"])
        with patch.object(self.module, "get_all_companies", return_value=[]):
            self.assertEqual(self.module.app.test_client().get("/api/regions/summary").json["regions"], [])
        with patch.object(self.module, "get_all_companies", side_effect=ValueError("Ошибка ключа")):
            self.assertEqual(self.module.app.test_client().get("/api/regions/summary").status_code, 500)

    def test_export_formula_protection(self):
        record = {**self.report, "company_name": '=HYPERLINK("https://example.com")'}
        csv_rows = list(csv.reader(io.StringIO(build_csv(record).decode("utf-8-sig")), delimiter=";"))
        self.assertTrue(csv_rows[0][1].startswith("'="))
        workbook = load_workbook(io.BytesIO(build_xlsx(record)))
        self.assertEqual(workbook.active["B1"].data_type, "s")
        self.assertEqual(workbook.active["B1"].value, record["company_name"])
        workbook.close()

    def test_download_for_both_flows(self):
        client = self.module.app.test_client()
        with patch.object(self.module, "generate_ai_report", return_value=self.report):
            manual = client.post("/api/manual-entry", json=self.company)
            uploaded = client.post("/api/analyze", data={"file": (
                io.BytesIO("name,revenue,employees,social_media\nКомпания,1000,0,высокая\n".encode()), "sample.csv",
            )})
        for result in (manual, uploaded):
            self.assertEqual(result.status_code, 200)
            company_id = result.json["company"]["id"]
            for extension, mime in (("pdf", "application/pdf"), ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("csv", "text/csv")):
                response = client.get(f"/api/report/{company_id}/download?format={extension}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, mime)
                self.assertIn(f"attachment; filename=otchet_{company_id}.{extension}", response.headers["Content-Disposition"])
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                if extension == "csv":
                    self.assertIn("Компания", response.data.decode("utf-8-sig"))
                    self.assertNotIn("gAAAA", response.data.decode("utf-8-sig"))

    def test_download_errors_and_unavailable_recommendation(self):
        client = self.module.app.test_client()
        self.assertEqual(client.get("/api/report/999999/download?format=csv").status_code, 404)
        self.assertEqual(client.get("/api/report/1/download?format=exe").status_code, 400)
        with patch.object(self.module, "client", None):
            result = client.post("/api/manual-entry", json=self.company)
        company_id = result.json["company"]["id"]
        response = client.get(f"/api/report/{company_id}/download?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Проверка нужна: Не определено", response.data.decode("utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
