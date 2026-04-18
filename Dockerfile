# Unified Root Dockerfile for Backend (Render often defaults to root path)
FROM python:3.11-slim
WORKDIR /app

# Copy and install backend dependencies explicitly from the backend directory
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory into the container
COPY backend/ /app/backend/

# Expose the API port
EXPOSE 8000

# Run the FastAPI server natively mapping to the root project structure
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
