FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
ENV PIPELINE_PORT=8021
EXPOSE 8021
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8021"]
