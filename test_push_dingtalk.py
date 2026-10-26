import unittest

import push_dingtalk


class GoldPushTest(unittest.TestCase):
    def test_50g_total_uses_latest_positive_quote(self):
        latest, week = push_dingtalk.gold_snapshot()
        self.assertGreater(float(latest["price"]) * 50, 0)
        self.assertEqual(latest, week[-1])
        self.assertLessEqual(len(week), 7)


if __name__ == "__main__":
    unittest.main()
