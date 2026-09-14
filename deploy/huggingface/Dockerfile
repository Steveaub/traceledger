FROM python:3.12-slim
RUN useradd --create-home --uid 1000 atlas
WORKDIR /app
COPY pyproject.toml README.md ./
COPY atlas ./atlas
RUN pip install --no-cache-dir .
COPY config ./config
COPY scripts/bootstrap_models.py ./scripts/bootstrap_models.py
RUN python scripts/bootstrap_models.py --retrieval-only && chmod -R a-w models
COPY data/synthetic ./data/synthetic
COPY data/public ./data/public
COPY data/conversations ./data/conversations
COPY reports/selection.json ./reports/selection.json
COPY reports/runs ./reports/runs
RUN mkdir -p data/index && chown -R atlas:atlas data/index
USER atlas
ENV ATLAS_DEMO=1 ATLAS_HOSTED_DEMO=1 HF_HUB_OFFLINE=1
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')"
CMD ["uvicorn", "atlas.api:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--no-proxy-headers"]
