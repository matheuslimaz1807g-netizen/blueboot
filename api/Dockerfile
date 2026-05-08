FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
# ... suas configurações anteriores ...
USER appuser

EXPOSE 8000


# Mude a linha do CMD para esta:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]