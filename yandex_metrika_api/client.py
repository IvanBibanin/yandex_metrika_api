from typing import Any, Iterable

import pandas as pd
import requests


class Yadnex_direct:
    """Client for loading reports from Yandex Metrica API."""

    API_URL = "https://api-metrika.yandex.net/stat/v1/data"

    def __init__(
        self,
        Tocen: Any = None,
        Login: str | Iterable[str] | None = None,
        Goals: Any = None,
        YM: int | str | Iterable[int | str] | None = None,
        DateFrom: str | None = None,
        DateTo: str | None = None,
    ):
        self.DateFrom = DateFrom
        self.DateTo = DateTo
        self.Tocen = Tocen
        self.Login = Login
        self.Goals = Goals
        self.YM = YM
        self.limit = 1000

        self.dimensions: str | Iterable[str] | None = None
        self.metrics: str | Iterable[str] | None = None
        self.Attribution = "automatic"

        self.df_origin = pd.DataFrame()
        self.custom_report_metrika_data: list[dict[str, Any]] = []

    @staticmethod
    def _to_csv(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, pd.Series):
            value = value.dropna().tolist()

        if isinstance(value, (list, tuple, set)):
            return ",".join(map(str, value))

        return str(value)

    @staticmethod
    def _to_list(value: Any) -> list[str]:
        if value is None:
            return []

        if isinstance(value, pd.Series):
            return [str(item) for item in value.dropna().tolist()]

        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]

        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value]

        return [str(value)]

    def _get_token(self) -> str:
        token = self.Tocen

        if isinstance(token, pd.Series):
            token = token.dropna().iloc[0] if not token.dropna().empty else ""
        elif isinstance(token, (list, tuple, set)):
            token = next(iter(token), "")

        return str(token).strip()

    def _handle_response(self, response: requests.Response, success_message: str = ""):
        """Handle Yandex Metrica API HTTP responses."""
        if response.status_code in (200, 201, 204):
            if success_message:
                print(success_message)

            if not response.text:
                return {}

            try:
                return response.json()
            except ValueError:
                print("API вернул не JSON")
                print(response.text[:300])
                return None

        if response.status_code == 400:
            print("Ошибка 400: неверный запрос или параметры")
        elif response.status_code == 401:
            print("Ошибка 401: пользователь не авторизован")
        elif response.status_code == 403:
            print("Ошибка 403: доступ запрещен или неверный OAuth-токен")
        elif response.status_code == 404:
            print("Ошибка 404: объект не найден")
        elif response.status_code == 406:
            print("Ошибка 406: неподдерживаемый формат")
        elif response.status_code == 409:
            print("Ошибка 409: конфликт или нарушение целостности данных")
        elif response.status_code == 429:
            print("Ошибка 429: превышен лимит запросов к API")
        elif response.status_code == 503:
            print("Ошибка 503: ошибка сервера, попробуйте позже")
        elif response.status_code == 504:
            print("Ошибка 504: запрос выполнялся слишком долго")
        elif 400 <= response.status_code < 500:
            print(f"Ошибка клиента: {response.status_code}")
        elif response.status_code >= 500:
            print(f"Ошибка сервера: {response.status_code}")
        else:
            print(f"Неожиданный статус API: {response.status_code}")

        if response.text:
            try:
                error_data = response.json()
                errors = error_data.get("errors", [])

                if errors:
                    first_error = errors[0]
                    print(f"Тип ошибки: {first_error.get('error_type')}")
                    print(f"Сообщение API: {first_error.get('message')}")
                elif error_data.get("message"):
                    print(f"Сообщение API: {error_data.get('message')}")
                else:
                    print(response.text[:300])
            except ValueError:
                print(response.text[:300])

        return None

    def get_report_metrika(self, offset: int = 1):
        headers = {"Authorization": "OAuth " + self._get_token()}
        params = {
            "ids": self._to_csv(self.YM),
            "date1": self.DateFrom,
            "date2": self.DateTo,
            "direct_client_logins": self._to_csv(self.Login),
            "limit": self.limit,
            "offset": offset,
            "dimensions": self._to_csv(self.dimensions),
            "metrics": self._to_csv(self.metrics),
            "attribution": self.Attribution,
            "accuracy": "full",
            "currency": "RUB",
            "group": "day",
        }
        params = {key: value for key, value in params.items() if value is not None}

        try:
            response = requests.get(
                self.API_URL,
                params=params,
                headers=headers,
                timeout=60,
            )
        except requests.RequestException as error:
            print(f"Ошибка запроса: {error}")
            return None

        print(response.status_code)
        result = self._handle_response(response)

        if result is None:
            return None

        return result.get("data", [])

    def full_report_metrica(self):
        """Post-page loading from Yandex Metrica."""
        full_data = []
        offset = 1

        while True:
            print("Starting offset {}".format(offset))
            data = self.get_report_metrika(offset=offset)

            if data is None:
                print("Выгрузка остановлена из-за ошибки API")
                return None

            full_data += data
            offset += self.limit

            if not data or len(data) < self.limit:
                break

        return full_data

    def custom_report_metrika(
        self,
        dimensions: str | Iterable[str] | None = None,
        metrics: str | Iterable[str] | None = None,
        Attribution: str = "automatic",
    ):
        self.dimensions = dimensions
        self.metrics = metrics
        self.Attribution = Attribution
        report = self.full_report_metrica()
        self.custom_report_metrika_data = report
        return report

    def to_dataframe(self, data) -> pd.DataFrame:
        if not data:
            self.df_origin = pd.DataFrame()
            return self.df_origin

        if isinstance(data, dict):
            data = data.get("data", [])

        dimensions = self._to_list(self.dimensions)
        metrics = self._to_list(self.metrics)
        rows = []

        for item in data:
            row = {}

            for column_name, value in zip(dimensions, item.get("dimensions", [])):
                row[column_name] = value.get("name")

            for column_name, value in zip(metrics, item.get("metrics", [])):
                row[column_name] = value

            rows.append(row)

        self.df_origin = pd.DataFrame(rows)
        return self.df_origin


YandexMetrica = Yadnex_direct
