FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run.sh ./

# Optional: copy .env.example for reference. The real .env should be supplied at
# runtime via `--env-file` or `-e KEY=VALUE` so secrets aren't baked into the image.
COPY .env.example ./

RUN chmod +x run.sh

EXPOSE 5000

CMD ["./run.sh"]
