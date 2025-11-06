# UnderPin_Notification
Notifications for UnderPin Vending

This is the Notification system for Underpin's Vending machines.

This is designed to be triggered via Google Cloud Scheduler once a day at 8am. 

This program hits the NAYAX api and retrieves a list of the last sales from each vending machine. It parses the list looking for the sales for the previous day, then builds a dictionary with customers as the key and a list of their sales as the value. Also builds a dictionary with products as the keys and customers as the values. 

It uses these dictionaries to email a notification to each customer listing their sales from the previous day. Each customer gets one email while an email is also sent to the main notification address. Program utilizes GMAIL SMTP to send emails. 

The program also creates multiple records in Google Sheets- one containing each notification that was sent, one containing a combined itemized receipt for each customers item including sales between multiple machines.  Program utilizes the GOOGLE SHEETS API to update sheets. 

Program is trigger from a Google Cloud Run Job. 

Files for the main functions are stored in the utils directory. 
Main.py is the main python file


DEPLOYMENT

-Create a Dockerfile ex:

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

Make sure to include secrets or sensitive files in a .dockerignore

-------------------------------------------------------------------------------------

# Set environmental variables
PROJECT_ID="your-gcp-project-id"
REGION="us-west2" 
IMAGE_NAME="my-job-image"
JOB_NAME="my-job-name"
REPO_NAME="GCP-artifact-repo-name"
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${IMAGE_NAME}:latest"

# Create a GCP artifact repo
gcloud artifacts repositories create ${REPO_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Repository for the daily underpin-notifications cron job image"

 # Authenticate Docker to push to Google Cloud
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Uploads to the Google Cloud Build service
gcloud builds submit --tag ${IMAGE_PATH} .

# Build the image using the Dockerfile and tag it for the registry
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${IMAGE_NAME}:latest .


# Build the image using the Dockerfile and tag it for the registry
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${IMAGE_NAME}:latest .




  
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