FROM python:3.12-slim

WORKDIR /app

# install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# install python dependencies with proper setuptools
COPY requirements.txt .
RUN pip install --upgrade pip "setuptools>=65.0.0" wheel && \
    pip install --no-cache-dir -r requirements.txt

# copy application code
COPY bot.py .

# Cloud Run injects PORT at runtime (default 8080)
ENV PORT=8080

# run as non-root for security
RUN useradd -m botuser
USER botuser

CMD ["python", "bot.py"]
