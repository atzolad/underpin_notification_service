# UnderPin_Notification
Notifications for UnderPin Vending

This is the Notification system for Underpin's Vending machines.

This is designed to be triggered via Google Cloud Scheduler once a day at 8am. 

This program hits the NAYAX api and retrieves a list of the last sales from each vending machine. It parses the list looking for the sales for the previous day, then builds a dictionary with customers as the key and a list of their sales as the value. Also builds a dictionary with products as the keys and customers as the values. 

It uses these dictionaries to email a notification to each customer listing their sales from the previous day. Each customer gets one email while an email is also sent to the main notification address. Program utilizes GMAIL SMTP to send emails. 

The program also creates multiple records in Google Sheets- one containing each notification that was sent, one containing a combined itemized receipt for each customers item including sales between multiple machines.  Program utilizes the GOOGLE SHEETS API to update sheets. 

In order to trigger the notification send- the file cron.py includes a minimal Flask app creating an endpoint for Google Cloud Scheduler to hit. The Cloud Scheduler should hit the main url for the service notification in google cloud to trigger this. ie https://google_service_url.us-west2.run.app/

Files for the main functions are stored in the utils directory. 
Main.py is the main python file
Cron.py is the file to execute for the Cloud Scheduler that will trigger main.py. In the dockerfile- use gunicorn to setup the HTTP server to serve the flask app and run cron.py: ex- CMD gunicorn --bind 0.0.0.0:$PORT cron:app


DEPLOYMENT

-Create a Dockerfile ex:

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


Make sure to include secrets or sensitive files in a .dockerignore

-------------------------------------------------------------------------------------

# Build the image and tag it for your Google Cloud registry. F flag sets the specific file (since it is not just Dockerignore)
docker build -f Dockerfile.cron -t gcr.io/{gcp-project_name}/{service_name}:latest .

# Authenticate Docker to GCR (if you haven't already)
gcloud auth configure-

# Push the Docker Image
docker push gcr.io/{gcp-project_name}/{service_name}:latest

# Build for amd64/linux architecture and push in one command- gcp runs this architecture.
docker buildx build -f Dockerfile.cron --platform linux/amd64 -t gcr.io/{gcp-project_name}/{service_name}:latest --push .

# Deploy the service
gcloud run deploy {service_name} \
    --image gcr.io/{gcp-project_name}/{service_name} :latest \
    --platform managed \
    --region us-west2 \
    --no-allow-unauthenticated \
    --max-instances 1 \
    --port 8080 # Cloud Run requires a port, though this script won't use it


  
-------------------------------------------------------------------------------------  

Need to add the environmental variables within the Google Cloud project. On the Cloud Console go to Cloud Run- click on the correct service. Click Edit and deploy new revision -> Variables and Secrets -> can add environmental variables there. Pasting the copied list from .env will populate them all.

# Create the scheduler job
gcloud scheduler jobs create http {scheduler_job_name} \
    --schedule="0 8 * * *" \
    --uri="{service_url/}“ \
    --http-method=POST \
    --location=us-west2 \
    --oidc-service-account-email="underpin-sales-notification@underpin-notification.iam.gserviceaccount.com" \
    --oidc-token-audience="{service_url} no / at the end“
    --time-zone="America/Los_Angeles"

# Immediately run to test

gcloud scheduler jobs run {scheduler_jobname} --location=us-west2