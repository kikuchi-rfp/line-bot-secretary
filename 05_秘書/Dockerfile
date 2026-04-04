# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Cloud Run uses PORT environment variable)
EXPOSE 8080

# Set environment variables
ENV PORT=8080

# Run the application
CMD ["python", "api.py"]
