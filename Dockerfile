# Production stage - AWS Lambda compatible
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Lambda-specific environment variables
ENV AWS_LWA_INVOKE_MODE=response_stream
ENV AWS_LAMBDA_RUNTIME_API=127.0.0.1:9001
ENV LAMBDA_TASK_ROOT=/var/task

WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies required for PyMuPDF, Playwright, and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies directly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install AWS Lambda Runtime Interface Client
RUN pip install --no-cache-dir awslambdaric

# Install Playwright browser (optimized for Lambda)
RUN python -m playwright install chromium --with-deps && \
    python -m playwright install-deps && \
    crawl4ai-setup && \
    (test -d /root/.cache/ms-playwright && chmod -R 755 /root/.cache/ms-playwright || true)

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Create the lambda function directory structure
RUN mkdir -p ${LAMBDA_TASK_ROOT}/src

# Set proper permissions for Lambda execution
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}

# Lambda handler configuration  
ENTRYPOINT ["python3", "-m", "awslambdaric"]
CMD ["lambda_handler.lambda_handler"]