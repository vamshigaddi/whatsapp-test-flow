# Use official lightweight Python 3.11 slim image
FROM python:3.11-slim

# Optimize Python execution in container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Google Cloud Run injects PORT environment variable (typically 8080)
ENV PORT=8080
EXPOSE 8080

# Start FastAPI server using uvicorn binding to 0.0.0.0 and Cloud Run's $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
