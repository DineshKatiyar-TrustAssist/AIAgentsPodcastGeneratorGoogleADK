# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
# Note: GOOGLE_API_KEY is NOT set here - users must enter it in the Streamlit UI
# Gmail SMTP credentials should be set via environment variables at runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Use pip 24.1 which has better resolver performance than 25.x
# Install in stages to avoid timeout issues and improve caching
RUN pip install --no-cache-dir "pip==24.1" setuptools wheel && \
    pip install --no-cache-dir --prefer-binary \
        python-dotenv>=1.0.0 \
        pydantic>=2.7.0 \
        pydub>=0.25.1 \
        PyPDF2>=3.0.0 \
        bcrypt>=4.1.2 \
        email-validator>=2.1.0 \
        tornado>=6.4 && \
    pip install --no-cache-dir --prefer-binary \
        google-auth>=2.27.0 \
        google-auth-oauthlib>=1.2.0 \
        google-auth-httplib2>=0.2.0 && \
    pip install --no-cache-dir --prefer-binary streamlit>=1.32.0 && \
    pip install --no-cache-dir --prefer-binary google-generativeai>=0.7.0 google-genai>=0.3.0 && \
    pip install --no-cache-dir --prefer-binary google-adk

# Copy application code
COPY app.py tools.py ./
COPY auth/ ./auth/

# Create necessary directories
RUN mkdir -p uploads outputs data

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

