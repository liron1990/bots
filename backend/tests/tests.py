import unittest

from app.common.messages import TemplateMerger  # שנה לפי שם הקובץ שלך

class TestTemplateMerger(unittest.TestCase):
    def setUp(self):
        self.data = {
            "macros": {
                "hello": "שלום {customerfirst} 👋",
                "message_end": "סיום"
            },
            "general": {
                "calander": {
                    "summary": "משחק {staffname}",
                    "description": "{message_end}",
                    "location": "פתח תקווה"
                }
            },
            "specific1": {
                "calander": {
                    "summary": "משחק ייחודי"
                }
            },
            "specific2": {
                "calander": {
                    "description": "התחלה {message_end}"
                }
            }
        }
        self.merger = TemplateMerger(self.data)

    def test_macro_expansion(self):
        self.assertEqual(self.merger["specific1"]["calander"]["summary"], "משחק ייחודי")
        self.assertEqual(self.merger["specific1"]["calander"]["description"], "סיום")  # נמשך מ-general ומפורש
        self.assertEqual(self.merger["specific2"]["calander"]["description"], "התחלה סיום")

    def test_fallback_location(self):
        self.assertEqual(self.merger["specific1"]["calander"]["location"], "פתח תקווה")
        self.assertEqual(self.merger["specific2"]["calander"]["location"], "פתח תקווה")


    def test_general_key(self):
        self.assertEqual(self.merger["general"]["calander"]["summary"], "משחק {staffname}")  # לא מחליף משתנים רגילים
        self.assertEqual(self.merger["general"]["calander"]["description"], "סיום")

    def test_missing_key_raises(self):
        self.assertEqual(self.merger["specific3"]["calander"]["location"], "פתח תקווה")

    def test_iteration_and_len(self):
        keys = list(self.merger)
        self.assertIn("specific1", keys)
        self.assertIn("specific2", keys)
        self.assertIn("general", keys)
        self.assertEqual(len(self.merger), 3)

if __name__ == "__main__":
    unittest.main()
