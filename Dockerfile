FROM python:3.12

WORKDIR /app

# install python dependencies - setuptools must be installed first and kept
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# copy application code  
COPY bot.py .

# Cloud Run injects PORT at runtime (default 8080)
ENV PORT=8080

# run as non-root for security
RUN useradd -m botuser
USER botuser

CMD ["python", "bot.py"]
