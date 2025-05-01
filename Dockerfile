FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# prevent Python from writing pyc files to disc (equivalent to python -B option):
ENV PYTHONDONTWRITEBYTECODE=1
# prevent Python from buffering stdout and stderr (equivalent to python -u option):
ENV PYTHONUNBUFFERED=1

# Run
CMD ["python", "./app.py"]
