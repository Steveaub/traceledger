FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY atlas ./atlas
RUN pip install --no-cache-dir .
COPY data/synthetic ./data/synthetic
COPY data/public ./data/public
COPY data/conversations ./data/conversations
COPY reports/selection.json ./reports/selection.json
COPY reports/runs ./reports/runs
RUN useradd --create-home atlas && mkdir -p data/index && chown -R atlas:atlas /app
USER atlas
ENV ATLAS_DEMO=0
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "atlas.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
