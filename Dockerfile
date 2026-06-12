FROM python:3.12

WORKDIR /app

# install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --upgrade setuptools wheel && \
    pip install -r requirements.txt && \
    python -c "import pkg_resources; print('pkg_resources OK')" && \
    python -c "from google.cloud import datastore; print('google-cloud-datastore OK')"

# copy application code  
COPY bot.py .

# Cloud Run injects PORT at runtime (default 8080)
ENV PORT=8080

# run as non-root for security
RUN useradd -m botuser
USER botuser

CMD ["python", "bot.py"]
