import contextlib
import io
import json
import unittest
from unittest.mock import patch

import requests

from class_yadnex_metrika import YadnexMetrika


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.client = YadnexMetrika(
            Tocen="test-token", YM=123, Login="test-login",
            DateFrom="2026-09-12", DateTo="2026-09-19",
        )
        contexts = contextlib.ExitStack()
        self.addCleanup(contexts.close)
        self.get = contexts.enter_context(patch("class_yadnex_metrika.requests.get"))
        self.sleep = contexts.enter_context(patch("class_yadnex_metrika.time.sleep"))
        contexts.enter_context(contextlib.redirect_stdout(io.StringIO()))

    @staticmethod
    def response(payload, status=200):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(payload).encode()
        response.url = "https://api-metrika.yandex.net/stat/v1/data"
        return response

    @staticmethod
    def row(date="2026-09-12", visits=2):
        return {"dimensions": [{"name": date}], "metrics": [visits]}

    def report(self):
        return self.client.custom_report_metrika(
            dimensions="ym:ad:date", metrics=["ym:ad:visits"],
        )

    def test_recovers_after_connection_and_read_timeouts(self):
        for error_type in (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            with self.subTest(error=error_type.__name__):
                self.get.reset_mock()
                self.sleep.reset_mock()
                self.get.side_effect = [
                    error_type("temporary"), self.response({"data": [self.row()]}),
                ]
                result = self.report()
                self.assertEqual(result.to_dict("records"), [
                    {"ym:ad:date": "2026-09-12", "ym:ad:visits": 2},
                ])
                self.assertEqual(self.get.call_count, 2)
                self.sleep.assert_called_once_with(1)
                for call in self.get.call_args_list:
                    self.assertEqual(call.kwargs["timeout"], (10, 120))
                    self.assertEqual(call.kwargs["params"]["offset"], 1)

    def test_exhausted_retries_raise_original_error(self):
        error = requests.exceptions.ConnectTimeout("unavailable")
        self.get.side_effect = error
        with self.assertRaises(requests.exceptions.ConnectTimeout) as caught:
            self.report()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.get.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2])

    def test_http_error_is_not_an_empty_report(self):
        for status in (400, 401, 403, 429, 503):
            with self.subTest(status=status):
                self.get.reset_mock()
                self.get.return_value = self.response(
                    {"errors": [{"error_type": "test_error", "message": "failed"}]},
                    status=status,
                )
                with self.assertRaises(requests.exceptions.HTTPError):
                    self.report()
                self.get.assert_called_once()
                self.sleep.assert_not_called()

    def test_empty_successful_report_remains_empty(self):
        self.get.return_value = self.response({"data": []})
        self.assertTrue(self.report().empty)
        self.get.assert_called_once()

    def test_invalid_report_is_not_treated_as_empty(self):
        for payload in ({}, {"data": None}, {"data": {}}, []):
            with self.subTest(payload=payload):
                self.get.return_value = self.response(payload)
                with self.assertRaisesRegex(ValueError, "ожидался список data"):
                    self.report()

    def test_non_json_response_raises(self):
        response = self.response({})
        response._content = b"not JSON"
        self.get.return_value = response
        with self.assertRaises(ValueError):
            self.report()

    def test_pagination_retries_same_page_without_duplicate_rows(self):
        self.client.limit = 1
        self.get.side_effect = [
            self.response({"data": [self.row()]}),
            requests.exceptions.ConnectTimeout("temporary"),
            self.response({"data": [self.row("2026-09-13", 3)]}),
            self.response({"data": []}),
        ]
        result = self.report()
        self.assertEqual(result["ym:ad:visits"].tolist(), [2, 3])
        self.assertEqual([
            call.kwargs["params"]["offset"] for call in self.get.call_args_list
        ], [1, 2, 2, 3])

    def test_failure_on_later_page_does_not_return_partial_report(self):
        self.client.limit = 1
        self.get.side_effect = [self.response({"data": [self.row()]})] + [
            requests.exceptions.ConnectTimeout("unavailable")
        ] * 3
        with self.assertRaises(requests.exceptions.ConnectTimeout):
            self.report()
        self.assertEqual(self.get.call_count, 4)


if __name__ == "__main__":
    unittest.main()
