import unittest
from unittest.mock import patch

import push_dingtalk


class GoldPushTest(unittest.TestCase):
    def test_50g_total_uses_latest_positive_quote(self):
        latest, week = push_dingtalk.gold_snapshot()
        self.assertGreater(float(latest["price"]) * 50, 0)
        self.assertEqual(latest, week[-1])
        self.assertLessEqual(len(week), 7)

    @patch("push_dingtalk.time.sleep")
    @patch("push_dingtalk.get_json", side_effect=[{"errcode": -1, "errmsg": "系统繁忙"}, {"errcode": 0}])
    def test_dingtalk_retries_transient_failure(self, get_json, sleep):
        push_dingtalk.send_dingtalk("https://example.invalid", {})
        self.assertEqual(get_json.call_count, 2)
        sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
