import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from console.collector import FORBIDDEN, REQUIRED_FILES, UPLOADS, set_submission
from console.main import STATE_PATH, app
from lab.store import get_grade, init_db, set_grade

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bing"


class UploadTest(unittest.TestCase):
    def setUp(self):
        self.grade = get_grade()
        self.state_existed = STATE_PATH.exists()
        self.state_bytes = STATE_PATH.read_bytes() if self.state_existed else None

    def tearDown(self):
        if get_grade() != self.grade:
            set_grade(self.grade)
            init_db()
        if self.state_bytes is None:
            if STATE_PATH.exists():
                STATE_PATH.unlink()
        else:
            STATE_PATH.write_bytes(self.state_bytes)

    def test_console_does_not_name_demo_dirs(self):
        root = Path(__file__).resolve().parents[1] / "console"
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").replace("\\", "/")
            self.assertNotIn("lab/evidence", text, path.name)
            self.assertNotIn("samples/other-system", text, path.name)
            self.assertNotIn("export_evidence", text, path.name)

    def test_submission_rejects_demo_directories(self):
        for banned in FORBIDDEN:
            with self.assertRaises(PermissionError):
                set_submission(banned)

    def test_missing_files_stop(self):
        client = TestClient(app)
        response = client.post(
            "/upload",
            files={"profile.json": ("profile.json", b"{}", "application/json")},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        page = client.get("/")
        for name in REQUIRED_FILES:
            if name != "profile.json":
                self.assertIn(name, page.text)
        self.assertIn("上传停住", page.text)

    def test_uploaded_json_is_judged_without_lab_evidence(self):
        client = TestClient(app)
        files = {
            name: (name, (FIXTURE / name).read_bytes(), "application/json")
            for name in REQUIRED_FILES
        }
        response = client.post("/upload", files=files, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["location"].endswith("/plan"))
        plan = client.get("/plan")
        self.assertEqual(plan.status_code, 200)
        started = client.post("/start", follow_redirects=False)
        self.assertEqual(started.status_code, 303)
        result = client.get("/result")
        self.assertIn("不符合", result.text)
        self.assertIn("通信机密性", result.text)
        submission = max(UPLOADS.glob("20*"), key=lambda item: item.name)
        self.assertTrue((submission / "profile.json").is_file())
        self.assertNotIn("lab/evidence", str(submission).replace("\\", "/"))

    def test_demo_download_zip_has_the_five_files(self):
        from lab.app.main import app as lab_app

        set_grade("丙")
        init_db()
        client = TestClient(lab_app)
        page = client.get("/")
        self.assertIn("下载本次材料", page.text)
        downloaded = client.get("/download")
        self.assertEqual(downloaded.status_code, 200)
        archive = zipfile.ZipFile(BytesIO(downloaded.content))
        self.assertEqual(set(archive.namelist()), set(REQUIRED_FILES))


if __name__ == "__main__":
    unittest.main()
