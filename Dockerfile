FROM selenium/standalone-chrome:143.0-20251212
LABEL maintainer="tomer.klein@gmail.com"

# Switch to root to install dependencies
USER root

ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV NOTIFIERS=""
ENV SCHEDULES=""

# Install required system dependencies
RUN apt-get update -yqq && \
    apt-get install -yqq python3-pip libffi-dev libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir

# Create app directory and set permissions
RUN mkdir -p /app/config && \
    chown -R seluser:seluser /app

# Copy application files
COPY app /app/

# Ensure correct permissions
RUN chown -R seluser:seluser /app

# Switch back to non-root user for security
USER seluser

WORKDIR /app
 
ENTRYPOINT ["python3", "/app/app.py"]