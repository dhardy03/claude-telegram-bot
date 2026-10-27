FROM python:3.12-slim

WORKDIR /app

# install python dependencies first so this layer is cached
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# only the server code; chat.py (local CLI with shell access) is not shipped
COPY bot.py .

# Cloud Run injects PORT at runtime (default 8080)
ENV PORT=8080

# run as non-root
RUN useradd -m botuser
USER botuser

CMD ["python", "bot.py"]
