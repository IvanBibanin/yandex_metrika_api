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
from class_yadnex_metrika import YadnexMetrika


df_yandex_metrika = df[df["Площадка"] == "Yandex_metrika"]
data = df_yandex_metrika.iloc[0]

Tocen = data["access_token"]
YM = data["ym"]
Login = data["Login"]
Goals = data["goals"]
schema = data["schema"]

ym = YadnexMetrika(
    Tocen=Tocen,
    Login=Login,
    YM=YM,
    Goals=Goals,
    DateFrom=DATE_FROM,
    DateTo=DATE_TO,
)

data = ym.custom_report_metrika(
    dimensions="ym:s:date",
    metrics="ym:s:visits",
)
```

## Формат ответа Метрики

API Яндекс Метрики возвращает строки отчета в таком формате:

```python
[
    {
        "dimensions": [{"name": "2026-05-18"}],
        "metrics": [512.0],
    }
]
```

После преобразования в `DataFrame` результат может выглядеть так:

```text
    ym:s:date  ym:s:visits
0  2026-05-18        512.0
```

## Что должен делать клиент

Класс для работы с API должен:

- отправлять запросы в `https://api-metrika.yandex.net/stat/v1/data`;
- поддерживать постраничную выгрузку через `limit` и `offset`;
- принимать `dimensions`, `metrics`, `date1`, `date2`, `ids`;
- обрабатывать HTTP-ошибки API;
- преобразовывать ответ Метрики в `pandas.DataFrame`.

## Обработка ошибок

При таймауте или ошибке соединения клиент делает до трех попыток запроса
каждой страницы, с паузами 1 и 2 секунды. Таймаут подключения — 10 секунд,
ожидания данных при чтении — 120 секунд.

Если все попытки неудачны, исключение `requests` передается вызывающему коду.
HTTP-ошибки вызывают `requests.exceptions.HTTPError`, а некорректный отчет —
`ValueError`. При ошибке на любой странице частичный отчет не возвращается.
Пустой `DataFrame` возвращается только для успешно полученного пустого отчета.
Перед созданием таблицы и удалением старых данных проверяйте `data.empty`:

```python
if data.empty:
    print("За выбранный период данных нет; обновление базы пропущено")
else:
    # Здесь создание таблицы, удаление старых строк и запись нового отчета.
    pass
```

Обновление установленного пакета в Jupyter:

```python
%pip install --upgrade git+https://github.com/IvanBibanin/yandex_metrika_api.git
```

После обновления перезапустите ядро ноутбука.

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

## Тесты

```bash
python -m unittest discover -s tests -v
```

Тесты используют имитации HTTP-ответов и не обращаются к API или базе данных.
