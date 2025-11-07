<h2 style="text-align:center;">Underpin Notification Service</h2>


Sales notification system for Underpin's Vending machines.


This program hits the NAYAX api and retrieves a list of the last sales from each vending machine. It parses the list looking for the sales for the previous day, then builds a dictionary with customers as the key and a list of their sales as the value. Also builds a dictionary with products as the keys and customers as the values. 

It uses these dictionaries and GOOGLE SMTP to email a notification to each customer with a html table listing their sales from the previous day. Each customer gets one email while an email is also sent to the main notification address.

The program also creates multiple records in Google Sheets using the Google Sheets API- one containing each notification that was sent, one containing a combined itemized receipt for each customer's item including sales between multiple machines. 

Program is deployed as a Google Cloud Run Job triggered via Google Cloud Scheduler once per day at 8AM PST. 

Main.py is the main executable python file. 
Files for the main functions are stored in the utils directory. 


## DEPLOYMENT:

### -Create a Dockerfile:

### Use a minimal Python base image
```bash
FROM python:3.13-slim
```

### Set working directory inside the container. If app directory doesn't exist, it creates it. 
```bash
WORKDIR /app
```

### Copy requirements first (for caching)
```bash
COPY requirements.txt .
```

###  Install dependencies
```bash
RUN pip install --no-cache-dir -r requirements.txt
```

###  Copy all necessary code into the app directory in the container
```bash
COPY . /app
```


### Run the notifcation program named main.py
```bash
CMD ["python", "main.py"]
```

### Make sure to include secrets or sensitive files in a .dockerignore

-------------------------------------------------------------------------------------


### Enable cloudbuild api
```bash
gcloud services enable cloudbuild.googleapis.com
```

### Set environmental variables
```bash
PROJECT_ID="your-gcp-project-id"
REGION="us-west2" 
IMAGE_NAME="my-job-image"
JOB_NAME="my-job-name"
REPO_NAME="GCP-artifact-repo-name"
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}"
```

### Check and see what docker images exist in the GCP artifacts repo
```bash
gcloud argcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/${IMAGE_NAME} --include-tags
```

### Create a GCP artifact repo
```bash
gcloud artifacts repositories create ${REPO_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Repository for the daily underpin-notifications cron job image"
```

    

### Authenticate Docker to push to Google Cloud
```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### Uploads to the Google Cloud Build service
```
gcloud builds submit --tag ${IMAGE_PATH} .
```

### Build the image using the Dockerfile and tag it for the registry
```
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}
```

### Check and see what docker images exist in the GCP artifacts repo
```
$ gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${JOB_NAME}/${IMAGE_NAME} --include-tags
```

##Create the cloud run job
```
gcloud run jobs create ${JOB_NAME} --image ${REGION}-docker.pkg.dev/${JOB_NAME}/${IMAGE_NAME}:latest --task-timeout "60s"
```
  
-------------------------------------------------------------------------------------  

### Add the environmental variables within the Google Cloud project: 

On the Cloud Console go to Cloud Run -> click on the correct service. Click Edit and deploy new revision -> Variables and Secrets -> add environmental variables there. Pasting the copied list from .env will populate them all. In this case I also mounted a volume from the Secrets manager with my credentials.json file containing Google API credentials. 



## Create the Google Cloud Scheduler Job to trigger notification service:

### Enable Cloud Scheduler API
```
gcloud services enable cloudscheduler.googleapis.com
```



### Define the name for the new Service Account (SA)
```
SCHEDULER_SA_NAME="cloud-scheduler-invoker"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
```

### Create the new Service Account
```
gcloud iam service-accounts create $SCHEDULER_SA_NAME \
    --display-name "Cloud Scheduler Invoker for Cloud Run Job"'
```

### Grant the new SA the 'Cloud Run Invoker' role for your job
```
gcloud run jobs add-iam-policy-binding $JOB_NAME \
    --region=$JOB_REGION \
    --member="serviceAccount:$SCHEDULER_SA_EMAIL" \
    --role="roles/run.invoker"

echo "Service Account $SCHEDULER_SA_EMAIL created and granted Invoker role."
```


### Set environmental variables for the scheduler job
```
SCHEDULER_SA_EMAIL="scheduler_email"
SCHEDULER_SA_NAME="scheduler_service_account_name"
SCHEDULER_NAME="scheduler_name"
PROJECT_ID="your-gcp-project-id"
REGION="us-west2" 
IMAGE_NAME="my-job-image"
JOB_NAME="my-job-name"
```
### Create the scheduler job
```
gcloud scheduler jobs create http $SCHEDULER_SA_NAME \
    --location=$REGION \
    --schedule="0 8 * * *" \
    --time-zone="America/Los_Angeles" \
    --uri="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email=$SCHEDULER_SA_EMAIL \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
    --project=$PROJECT_ID
```

### Immediately run to test
```
gcloud scheduler jobs run $SCHEDULER_NAME --location=$REGION
```