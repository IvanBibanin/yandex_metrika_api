from datetime import datetime as dt, timedelta
import pandas as pd
import numpy as np
import requests
import time
from typing import Any




class YadnexMetrika:
    def __init__(self, Tocen=None, Login=None, Goals=None, YM=None, DateFrom=None, DateTo=None):
        self.DateFrom = DateFrom
        self.DateTo = DateTo
        self.Tocen = Tocen
        self.Login = Login
        self.Goals = Goals
        self.YM = YM
        self.coll = []
        self.chat_id = None
        self.limit = 1000

    @staticmethod
    def _split_columns(value):
        if value is None:
            return []

        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]

        if isinstance(value, (list, tuple, set)):
            columns = []
            for item in value:
                if isinstance(item, str):
                    columns.extend(part.strip() for part in item.split(",") if part.strip())
                else:
                    columns.append(str(item))
            return columns

        return [str(value)]

    @classmethod
    def _to_csv(cls, value):
        columns = cls._split_columns(value)
        if not columns:
            return None
        return ",".join(columns)

    def _handle_response(self, response, success_message=""):
        """Общая обработка ответов API Яндекс Метрики."""
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
    
        print(f"Ошибка API: {response.status_code}")
    
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


    def get_report_metrika(self, offset=1):
        url = 'https://api-metrika.yandex.net/stat/v1/data'
        headers = {'Authorization': 'OAuth ' + str(f'{self.Tocen}')}
        params = {
            'ids': self.YM,
            "date1": self.DateFrom,
            "date2": self.DateTo,
            "direct_client_logins": self.Login,
            "limit": self.limit,
            "offset": offset,
            "dimensions": self._to_csv(self.dimensions),
            "metrics": self._to_csv(self.metrics),
            "attribution": self.Attribution,
            'accuracy': 'full',
            "currency": "RUB",
            'group': 'day'
        }

        for attempt in range(3):
            try:
                response = requests.get(
                    url, params=params, headers=headers, timeout=(10, 120)
                )
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

        print(response.status_code)
        result = self._handle_response(response)
        response.raise_for_status()

        if not isinstance(result, dict) or not isinstance(result.get('data'), list):
            raise ValueError("API Метрики вернул некорректный отчет: ожидался список data")

        return result['data']

    def full_report_metrica(self):
        """Постраничная выгрузка из Метрики"""
        full_data = []
        offset = 1

        while True:
            print('Starting offset {}'.format(offset))
            data = self.get_report_metrika(offset=offset)

            if data is None:
                raise RuntimeError("Выгрузка остановлена из-за ошибки API")

            full_data += data

            offset += self.limit

            if not data or len(data) < self.limit:
                break

        return full_data

    def custom_report_metrika(self, dimensions=None, metrics=None, Attribution="Automatic"):
        self.dimensions = dimensions
        self.metrics = metrics
        self.Attribution = Attribution
        report = self.full_report_metrica()
        self.custom_report_metrika_data = report
        df = self.to_dataframe(self.custom_report_metrika_data)
        return df
        
    def to_dataframe(self, data):
        if not data:
            self.df_origin = pd.DataFrame()
            return self.df_origin
    
        dimensions = self._split_columns(self.dimensions)
        metrics = self._split_columns(self.metrics)

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
