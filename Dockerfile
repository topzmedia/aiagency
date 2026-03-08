FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ai_ad_agency/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn jinja2 python-multipart

# Copy app code
COPY ai_ad_agency/ ./ai_ad_agency/

# Create outputs directory
RUN mkdir -p /app/ai_ad_agency/outputs

# Expose port
EXPOSE 8000

# Start server at /agency root path
CMD ["uvicorn", "ai_ad_agency.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
