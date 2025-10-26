FROM python:3.11-slim
WORKDIR /docs
RUN pip install --no-cache-dir mkdocs-material mkdocs-mermaid2-plugin
COPY . /docs
EXPOSE 8020
CMD ["mkdocs", "serve", "-a", "0.0.0.0:8020"]
