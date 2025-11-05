#  Use a minimal Python base image
FROM python:3.13-slim

# Set working directory inside the container. If app directory doesn't exist, it creates it. 
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

#  Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

#  Copy all necessary code into the app directory in the container

COPY . /app


# Run the notifcation program named main.py
CMD ["python", "main.py"]