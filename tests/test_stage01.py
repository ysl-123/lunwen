import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from console.collector import AddressRejected, check_target
from console.rules import REPORT_FIRST_LINE, build_plan, judge, load_clauses
from lab.store import DB_PATH, EVIDENCE_DIR, init_db, set_grade
from tests.support import use_fixture


class Stage01Test(unittest.TestCase):
    def test_whitelist_rejects_other_hosts(self):
        for url in (
            "http://8.8.8.8/",
            "http://localhost:8000/",
            "https://127.0.0.1:8000/",
            "http://127.0.0.1:443/",
            "http://evil.example/",
        ):
            with self.assertRaises(AddressRejected):
                check_target(url)
        self.assertEqual(check_target("http://127.0.0.1:8000/login"), "http://127.0.0.1:8000")
        self.assertEqual(check_target("https://127.0.0.1:8443/login"), "https://127.0.0.1:8443")
        self.assertEqual(check_target("gm://127.0.0.1:9443"), "gm://127.0.0.1:9443")

    def test_login_and_plaintext_rows(self):
        from lab.app.main import app

        set_grade("丙")
        init_db()
        client = TestClient(app)
        page = client.get("/")
        self.assertEqual(page.status_code, 200)
        bad = client.post("/login", data={"username": "test", "password": "nope"})
        self.assertEqual(bad.status_code, 401)
        ok = client.post(
            "/login",
            data={"username": "test", "password": "123456"},
            follow_redirects=False,
        )
        self.assertEqual(ok.status_code, 303)
        profile = client.get("/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertIn("13800000000", profile.text)
        rows = (EVIDENCE_DIR / "rows.json").read_text(encoding="utf-8")
        self.assertIn('"password": "123456"', rows)
        self.assertIn('"phone": "13800000000"', rows)
        self.assertTrue(DB_PATH.exists())

    def test_rules_both_noncompliant(self):
        use_fixture("bing")
        from console.collector import collect_for_units

        facts = collect_for_units()
        results = judge(facts)
        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["通信机密性"]["result"], "不符合")
        self.assertEqual(by_name["存储机密性"]["result"], "不符合")
        for name in ("通信机密性", "存储机密性"):
            self.assertTrue(by_name[name]["fact_ids"])
        from console.rules import build_report

        report = build_report(results, facts)
        self.assertTrue(report.startswith(REPORT_FIRST_LINE))
        self.assertIn("F-002", report)
        self.assertIn("F-004", report)
        self.assertNotIn("密评通过", report)

    def test_stage2_plan_matches_clause_card(self):
        raw = (Path(__file__).resolve().parents[1] / "clauses.json").read_text(encoding="utf-8")
        clauses = load_clauses()
        self.assertGreaterEqual(len(clauses), 39)
        layers = {item["layer"] for item in clauses}
        self.assertTrue(
            {"物理和环境", "网络和通信", "设备和计算", "应用和数据", "管理制度", "人员管理", "建设运行", "应急处置"}
            <= layers
        )
        for item in clauses:
            self.assertIn(item["strength"], {"应", "宜", "可"})
            self.assertIsInstance(item["high_risk"], bool)
            self.assertIn(item["excerpt"], raw)
        units = build_plan()
        self.assertEqual(len(units), len(clauses))
        for unit, clause in zip(units, clauses):
            self.assertEqual(unit["excerpt"], clause["excerpt"])
            self.assertEqual(unit["strength"], clause["strength"])
            self.assertIn(unit["excerpt"], raw)
        from console.rules import CHECKLIST_LAYERS

        technical = {
            "NET-CONF",
            "DEV-AUTH",
            "DEV-REMOTE",
            "DEV-ACL",
            "DEV-LABEL",
            "DEV-LOG",
            "DEV-BIN",
            "APP-AUTH",
            "APP-ACL",
            "APP-TRANS-CONF",
            "APP-STORE-CONF",
            "APP-TRANS-INT",
            "APP-STORE-INT",
            "APP-NR",
        }
        for unit in units:
            if unit["layer"] in CHECKLIST_LAYERS or unit["clause_id"] in technical:
                self.assertTrue(unit["judged"], unit["clause_id"])
            else:
                self.assertFalse(unit["judged"], unit["clause_id"])
                self.assertEqual(unit["object"], "未提供对象")
        high = {unit["clause_id"] for unit in units if unit["high_risk"]}
        self.assertTrue({"NET-AUTH", "NET-CONF", "DEV-AUTH", "DEV-REMOTE", "APP-AUTH", "APP-TRANS-CONF", "APP-STORE-CONF"} <= high)

    def test_stage4_device_and_app_items_are_filled(self):
        use_fixture("bing")
        from console.collector import collect_for_units

        results = {item["clause_id"]: item for item in judge(collect_for_units())}
        required = [
            "DEV-AUTH",
            "DEV-REMOTE",
            "DEV-ACL",
            "DEV-LABEL",
            "DEV-LOG",
            "DEV-BIN",
            "APP-AUTH",
            "APP-ACL",
            "APP-TRANS-CONF",
            "APP-STORE-CONF",
            "APP-TRANS-INT",
            "APP-STORE-INT",
            "APP-NR",
        ]
        for clause_id in required:
            item = results[clause_id]
            self.assertIn(item["result"], {"符合", "部分符合", "不符合", "证据不足"})
            self.assertTrue(item["fact_ids"], clause_id)
            self.assertNotEqual(item["result"], "")
        self.assertEqual(results["APP-AUTH"]["result"], "不符合")
        self.assertIn("F-006", results["APP-AUTH"]["fact_ids"])
        for clause_id in ("DEV-LOG", "DEV-BIN", "APP-STORE-INT", "APP-NR"):
            self.assertEqual(results[clause_id]["result"], "证据不足")

    def test_stage5_blank_checklist_is_not_compliant(self):
        from console.rules import CHECKLIST_LAYERS, build_report

        use_fixture("bing")
        from console.collector import collect_for_units

        facts = collect_for_units()
        results = judge(facts)
        layers = {item["id"]: item["layer"] for item in load_clauses()}
        checklist_results = [item for item in results if layers.get(item["clause_id"]) in CHECKLIST_LAYERS]
        self.assertTrue(checklist_results)
        self.assertTrue(all(item["result"] == "未提供" for item in checklist_results))
        self.assertNotIn("物理访问身份鉴别", [item["name"] for item in results if item["result"] == "符合"])
        report = build_report(results, facts)
        provided, _, _rest = report.partition("## 未提供")
        self.assertNotIn("物理访问身份鉴别", provided)
        self.assertIn("### 物理访问身份鉴别", report)

    def test_stage5_fake_filename_is_not_compliant(self):
        from console.rules import CHECKLIST_LAYERS, build_report

        dest = use_fixture("bing")
        fake = "随便一个字.txt"
        materials = dest / "materials"
        materials.mkdir(parents=True, exist_ok=True)
        self.assertFalse((materials / fake).exists())
        outside = "../rows.json"
        empty_name = "empty-note.txt"
        (materials / empty_name).write_text("这里只有一句无关的话。", encoding="utf-8")
        quoted_name = "phy-auth.txt"
        excerpt = next(item["excerpt"] for item in load_clauses() if item["id"] == "PHY-AUTH")
        (materials / quoted_name).write_text("现场记录。\n" + excerpt + "\n以上。", encoding="utf-8")
        matched_name = "mgmt-procedure.txt"
        matched = next(item["excerpt"] for item in load_clauses() if item["id"] == "MGMT-PROCEDURE")
        (materials / matched_name).write_text(matched, encoding="utf-8")
        chosen = {
            "PHY-AUTH": fake,
            "PHY-GATE": outside,
            "PHY-VIDEO": empty_name,
            "MGMT-POLICY": quoted_name,
            "MGMT-PROCEDURE": matched_name,
        }
        items = []
        for clause in load_clauses():
            if clause["layer"] not in CHECKLIST_LAYERS:
                continue
            items.append(
                {
                    "id": f"F-CL-{clause['id']}",
                    "clause_id": clause["id"],
                    "filename": chosen.get(clause["id"], ""),
                }
            )
        checklist = dest / "checklist.json"
        checklist.write_text(json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")
        from console.collector import collect_for_units

        facts = collect_for_units()
        results = {item["clause_id"]: item for item in judge(facts)}
        self.assertEqual(results["PHY-AUTH"]["result"], "未提供")
        self.assertEqual(results["PHY-GATE"]["result"], "未提供")
        self.assertEqual(results["PHY-VIDEO"]["result"], "证据不足")
        self.assertEqual(results["NET-CONF"]["result"], "不符合")
        self.assertEqual(results["APP-STORE-CONF"]["result"], "不符合")
        policy = next(item["excerpt"] for item in load_clauses() if item["id"] == "MGMT-POLICY")
        self.assertNotEqual(results["MGMT-POLICY"]["result"], "符合")
        self.assertNotIn(policy, (materials / quoted_name).read_text(encoding="utf-8"))
        self.assertEqual(results["MGMT-PROCEDURE"]["result"], "符合")
        self.assertEqual(results["MGMT-PROCEDURE"]["material_quote"], matched)
        self.assertIn(matched, (materials / matched_name).read_text(encoding="utf-8"))
        report = build_report(list(results.values()), facts)
        self.assertNotIn(f"材料摘录：{excerpt}", report)
        self.assertIn(f"材料摘录：{matched}", report)
        self.assertNotIn("lab/evidence", str(dest).replace("\\", "/"))

    def test_stage6_old_report_remains(self):
        from console.main import save_run

        first = save_run("送评前预检，非正式密评\n\n第一份\n", [])
        second = save_run("送评前预检，非正式密评\n\n第二份\n", [])
        self.assertNotEqual(first, second)
        self.assertTrue((first / "report.md").exists())
        self.assertTrue((second / "report.md").exists())
        self.assertIn("第一份", (first / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
