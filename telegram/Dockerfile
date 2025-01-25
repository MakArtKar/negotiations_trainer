FROM python:3.10

WORKDIR /app/telegram

# Установка зависимостей для Poetry и других нужных пакетов
RUN apt-get update && apt-get install -y curl gcc

# Установка Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Добавление Poetry в PATH
ENV PATH="/root/.local/bin:$PATH"

# Копирование конфигурационных файлов Poetry
COPY telegram/pyproject.toml /app/telegram/

# Копирование исходного кода приложения
COPY telegram /app/telegram

# Установка зависимостей проекта с новой опцией --only main
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root

# Запуск uvicorn
CMD ["python", "main.py"]
