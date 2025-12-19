# Deployment Guide for Google Cloud Platform

This guide covers deploying the AI Agents Podcast Generator to Google Cloud Platform using Cloud Run or App Engine.

## Prerequisites

1. **Google Cloud Account**: Sign up at [Google Cloud Platform](https://cloud.google.com/)
2. **Google Cloud SDK**: Install [gcloud CLI](https://cloud.google.com/sdk/docs/install)
3. **Docker**: Install [Docker](https://www.docker.com/get-started) (for local testing)
4. **Billing**: Enable billing on your GCP project

## Option 1: Deploy to Cloud Run (Recommended)

Cloud Run is a serverless platform that automatically scales your application.

### Step 1: Set Up GCP Project

```bash
# Login to GCP
gcloud auth login

# Set your project ID
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 2: Configure Secrets

Store your API keys in Secret Manager:

```bash
# Create secrets
echo -n "your-google-api-key" | gcloud secrets create google-api-key --data-file=-
echo -n "Puck" | gcloud secrets create sarah-voice-name --data-file=-
echo -n "Kore" | gcloud secrets create dennis-voice-name --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding google-api-key \
    --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Step 3: Build and Deploy

#### Using Cloud Build (Recommended)

1. **Create a Cloud Build trigger** (via Console or CLI):

```bash
gcloud builds triggers create github \
    --repo-name=your-repo-name \
    --repo-owner=your-github-username \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml \
    --substitutions=_GOOGLE_API_KEY=$(gcloud secrets versions access latest --secret=google-api-key)
```

2. **Or build and deploy manually**:

```bash
# Build the image
gcloud builds submit --tag gcr.io/$PROJECT_ID/podcast-generator

# Deploy to Cloud Run
gcloud run deploy podcast-generator \
    --image gcr.io/$PROJECT_ID/podcast-generator \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8501 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --set-secrets="GOOGLE_API_KEY=google-api-key:latest,SARAH_VOICE_NAME=sarah-voice-name:latest,DENNIS_VOICE_NAME=dennis-voice-name:latest"
```

#### Using Docker Locally

```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/podcast-generator .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/podcast-generator

# Deploy to Cloud Run
gcloud run deploy podcast-generator \
    --image gcr.io/$PROJECT_ID/podcast-generator \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8501 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --set-secrets="GOOGLE_API_KEY=google-api-key:latest"
```

### Step 4: Access Your Application

After deployment, Cloud Run will provide a URL like:
```
https://podcast-generator-xxxxx-uc.a.run.app
```

## Option 2: Deploy to App Engine

App Engine provides a fully managed platform with automatic scaling.

### Step 1: Set Up GCP Project

```bash
# Login and set project
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable App Engine
gcloud app create --region=us-central
```

### Step 2: Configure Environment Variables

Set environment variables in App Engine:

```bash
# Set secrets in Secret Manager (same as Cloud Run)
echo -n "your-google-api-key" | gcloud secrets create google-api-key --data-file=-

# Deploy with environment variables
gcloud app deploy app.yaml \
    --set-env-vars="GOOGLE_API_KEY=$(gcloud secrets versions access latest --secret=google-api-key),SARAH_VOICE_NAME=Puck,DENNIS_VOICE_NAME=Kore"
```

### Step 3: Deploy

```bash
gcloud app deploy
```

### Step 4: Access Your Application

```bash
# Get the URL
gcloud app browse
```

## Option 3: Deploy to Compute Engine (VM)

For more control, deploy to a VM instance.

### Step 1: Create VM Instance

```bash
gcloud compute instances create podcast-generator-vm \
    --zone=us-central1-a \
    --machine-type=e2-standard-4 \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --boot-disk-size=20GB
```

### Step 2: Install Docker and Deploy

```bash
# SSH into the VM
gcloud compute ssh podcast-generator-vm --zone=us-central1-a

# Install Docker (on Container-Optimized OS, Docker is pre-installed)
# Pull and run your image
docker run -d \
    -p 8501:8501 \
    -e GOOGLE_API_KEY=your-api-key \
    -e SARAH_VOICE_NAME=Puck \
    -e DENNIS_VOICE_NAME=Kore \
    gcr.io/$PROJECT_ID/podcast-generator
```

## Environment Variables

The application requires the following environment variables:

- **GOOGLE_API_KEY** (required): Your Google API key for Gemini and TTS
- **SARAH_VOICE_NAME** (optional): Google TTS voice for Sarah (default: "Puck")
- **DENNIS_VOICE_NAME** (optional): Google TTS voice for Dennis (default: "Kore")

## Resource Requirements

### Recommended Settings:

- **Memory**: 2GB minimum (4GB recommended for large PDFs)
- **CPU**: 2 vCPUs minimum
- **Timeout**: 3600 seconds (1 hour) for long-running podcast generation
- **Storage**: Ephemeral storage for temporary files (uploads/ and outputs/)

### Cloud Run Specific:

- **Min Instances**: 0 (for cost savings) or 1 (for faster cold starts)
- **Max Instances**: 10 (adjust based on expected traffic)
- **Concurrency**: 10 requests per instance (default)

## Monitoring and Logging

### View Logs

```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=podcast-generator" --limit 50

# App Engine logs
gcloud app logs tail -s default
```

### Set Up Monitoring

1. Go to Cloud Console → Monitoring
2. Create alerts for:
   - High error rates
   - High latency
   - Resource usage (CPU, memory)

## Cost Optimization

### Cloud Run:

- Set `min-instances=0` to scale to zero when not in use
- Use appropriate memory/CPU settings (don't over-provision)
- Set reasonable `max-instances` based on traffic

### App Engine:

- Use automatic scaling with appropriate min/max instances
- Enable request logging only when needed

## Troubleshooting

### Common Issues:

1. **Out of Memory Errors**:
   - Increase memory allocation (2Gi → 4Gi)
   - Check for memory leaks in long-running processes

2. **Timeout Errors**:
   - Increase timeout (default 300s → 3600s for Cloud Run)
   - Optimize PDF processing for large files

3. **API Key Errors**:
   - Verify secrets are correctly set in Secret Manager
   - Check IAM permissions for secret access

4. **Port Issues**:
   - Ensure port 8501 is exposed in Dockerfile
   - Verify Cloud Run port configuration matches

### Debug Commands:

```bash
# Check Cloud Run service status
gcloud run services describe podcast-generator --region us-central1

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit 20

# Test locally with Docker
docker run -p 8501:8501 -e GOOGLE_API_KEY=your-key gcr.io/$PROJECT_ID/podcast-generator
```

## CI/CD Setup

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - id: 'auth'
        uses: 'google-github-actions/auth@v1'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      
      - name: 'Set up Cloud SDK'
        uses: 'google-github-actions/setup-gcloud@v1'
      
      - name: 'Build and Deploy'
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT }}/podcast-generator
          gcloud run deploy podcast-generator \
            --image gcr.io/${{ secrets.GCP_PROJECT }}/podcast-generator \
            --platform managed \
            --region us-central1
```

## Security Best Practices

1. **Use Secret Manager** for API keys (never commit to code)
2. **Enable IAM** to control access
3. **Use HTTPS** (automatic with Cloud Run/App Engine)
4. **Set up VPC** for private networking if needed
5. **Enable Cloud Armor** for DDoS protection
6. **Regular updates** of base images and dependencies

## Support

For issues or questions:
- Check [Google Cloud Documentation](https://cloud.google.com/docs)
- Review [Cloud Run Documentation](https://cloud.google.com/run/docs)
- Check application logs in Cloud Console

