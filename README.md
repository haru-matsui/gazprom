# gazprom


## Настройка
Создайте файл `.env` на основе шаблона и вставьте в него рабочий API-ключ:
команда

```bash
cp template.env .env
```

## Запуск

### Backend

```bash
uvicorn main:app --reload --port 8000
````

### Frontend

```bash
streamlit run frontend.py
```