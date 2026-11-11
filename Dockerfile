# Build local, na raiz do repositório: docker build -t ccaa:local .
FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CCAA_HOST=0.0.0.0 \
    CCAA_PORT=8876

WORKDIR /app

RUN groupadd --gid 1000 ccaa \
    && useradd --uid 1000 --gid ccaa --no-create-home ccaa

COPY testes/requirements.txt ./testes/requirements.txt
RUN python -m pip install --no-cache-dir -r testes/requirements.txt

COPY --chown=ccaa:ccaa testes/preview_server.py testes/gerencial.py testes/lote.py testes/hosted.py testes/preview_AGENDA_*.py ./testes/
COPY --chown=ccaa:ccaa testes/web/ ./testes/web/
COPY --chown=ccaa:ccaa testes/templates/ ./testes/templates/
COPY --chown=ccaa:ccaa testes/lote_outlook/executar.ps1 testes/lote_outlook/abrir.cmd testes/lote_outlook/LEIA-ME.txt ./testes/lote_outlook/
COPY --chown=ccaa:ccaa fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html ./fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html

RUN mkdir -p /app/databases && chown ccaa:ccaa /app/databases

USER ccaa
EXPOSE 8876

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('CCAA_PORT', '8876') + '/healthz', timeout=3).close()"

CMD ["python", "testes/preview_server.py"]
