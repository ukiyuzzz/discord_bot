import unittest

from services.moderation_parser import parse_timeout_request


class ModerationParserTests(unittest.TestCase):
    def test_parse_timeout_request_with_minutes(self):
        target, duration_seconds = parse_timeout_request("тайм-аут @alice на 10 минут")
        self.assertEqual(target, "alice")
        self.assertEqual(duration_seconds, 600)

    def test_parse_timeout_request_with_hours(self):
        target, duration_seconds = parse_timeout_request("отправь Святослава в тайм-аут на 2 часа")
        self.assertEqual(target, "Святослава")
        self.assertEqual(duration_seconds, 7200)

    def test_parse_timeout_request_with_minutes_alias(self):
        target, duration_seconds = parse_timeout_request("выдай мут @user на 30 мин")
        self.assertEqual(target, "user")
        self.assertEqual(duration_seconds, 1800)


if __name__ == "__main__":
    unittest.main()
