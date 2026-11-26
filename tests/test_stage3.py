import unittest
from pathlib import Path

from console.collector import collect_for_units
from console.rules import judge
from tests.support import use_fixture

ROOT = Path(__file__).resolve().parents[1]


def load_truth() -> dict:
    current = None
    data: dict[str, dict[str, str]] = {}
    for line in (ROOT / "lab" / "ground-truth.yaml").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if not line.startswith(" "):
            current = line.split(":", 1)[0].strip()
            data[current] = {}
        else:
            name, value = line.strip().split(":", 1)
            data[current][name.strip()] = value.strip()
    return data


def judged(fixture: str) -> dict[str, str]:
    use_fixture(fixture)
    return {item["name"]: item["result"] for item in judge(collect_for_units())}


def same_as_truth(result: dict[str, str], expected: dict[str, str]) -> bool:
    return {name: result[name] for name in expected} == expected


class Stage3Test(unittest.TestCase):
    def test_grades_match_answer_book(self):
        truth = load_truth()
        self.assertTrue(same_as_truth(judged("yi"), truth["乙"]))
        self.assertTrue(same_as_truth(judged("jia"), truth["甲"]))
        self.assertTrue(same_as_truth(judged("bing"), truth["丙"]))


if __name__ == "__main__":
    unittest.main()
