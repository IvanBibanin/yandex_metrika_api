# yandex_metrika_api

Проект для выгрузки отчетов из API Яндекс Метрики и превращения ответа в `pandas.DataFrame`.

## Установка

```bash
pip install git+https://github.com/IvanBibanin/yandex_metrika_api.git
```

Для локальной разработки:

```bash
git clone https://github.com/IvanBibanin/yandex_metrika_api.git
cd yandex_metrika_api
pip install -e .
```

## Зависимости

- `requests`
- `pandas`

## Пример использования

```python
ym = Yadnex_direct(
    Tocen="your_oauth_token",
    YM=12345678,
    DateFrom="2026-05-01",
    DateTo="2026-05-23",
)

data = ym.custom_report_metrika(
    dimensions="ym:s:date",
    metrics="ym:s:visits",
)

df = ym.to_dataframe(data)
print(df)
```

Пример результата:

```text
    ym:s:date  ym:s:visits
0  2026-05-18        512.0
```

## Несколько метрик и группировок

```python
data = ym.custom_report_metrika(
    dimensions=["ym:s:date", "ym:s:lastTrafficSource"],
    metrics=["ym:s:visits", "ym:s:users"],
    Attribution="automatic",
)

df = ym.to_dataframe(data)
```

## Обработка ошибок

Общую обработку ответов API удобно вынести в отдельный метод `_handle_response()`. Основные коды ошибок:

- `400` - неверный запрос или параметры
- `401` - пользователь не авторизован
- `403` - доступ запрещен или неверный OAuth-токен
- `404` - объект не найден
- `406` - неподдерживаемый формат
- `409` - конфликт или нарушение целостности данных
- `429` - превышен лимит запросов к API
- `503` - ошибка сервера
- `504` - запрос выполнялся слишком долго

Если API возвращает `error_type` и сообщение об ошибке, их тоже стоит выводить в консоль.
