#  Use a minimal Python base image
FROM python:3.13-slim

# Set working directory inside the container. If app directory doesn't exist, it creates it. 
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

#  Install dependencies (including Flask, which is in your cron.py)
RUN pip install --no-cache-dir -r requirements.txt

#  Copy all necessary code into the app directory in the container

COPY . /app

#  Expose port (Good practice, though not strictly necessary for Cloud Run)
EXPOSE 8080

#Set the flask environment so it doesn't setup the local development server
ENV FLASK_ENV='production'

# Run the Flask server named "app" with Gunicorn from the cron.py file
CMD gunicorn --bind 0.0.0.0:$PORT cron:app