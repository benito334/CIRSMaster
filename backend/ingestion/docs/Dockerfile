FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
ENV PDF_INPUT_PATH=/data/ingestion/pdf \
    EPUB_INPUT_PATH=/data/ingestion/epub \
    OUTPUT_PATH=/data/transcripts
CMD ["python", "main.py"]
