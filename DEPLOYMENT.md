# Smart-Aleck Backend Deployment Guide

## Overview
This guide provides instructions for deploying the Smart-Aleck backend to Amazon Web Services (AWS).

## Prerequisites
- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Docker installed (for containerized deployment)
- Environment variables configured

## Environment Variables
Create a `.env` file with the following variables:

```env
# Database Configuration
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=your_pinecone_index_name

# Django Configuration
SECRET_KEY=your_django_secret_key
DEBUG=False
ALLOWED_HOSTS=your_domain.com,your_ip_address
```

## Deployment Options

### Option 1: AWS Elastic Beanstalk
1. Install EB CLI: `pip install awsebcli`
2. Initialize EB application: `eb init`
3. Create environment: `eb create production`
4. Deploy: `eb deploy`

### Option 2: AWS EC2 with Docker
1. Launch EC2 instance
2. Install Docker on the instance
3. Build Docker image: `docker build -t smart-aleck-backend .`
4. Run container: `docker run -d -p 80:8000 --env-file .env smart-aleck-backend`

### Option 3: AWS ECS (Recommended for production)
1. Create ECS cluster
2. Define task definition with container specifications
3. Create service to run the task
4. Configure load balancer and auto-scaling

## Database Setup
1. Create RDS MySQL instance
2. Configure security groups for database access
3. Run migrations: `python manage.py migrate`
4. Create superuser: `python manage.py createsuperuser`

## Static Files
Configure static file serving:
1. Set `STATIC_ROOT` in settings.py
2. Run `python manage.py collectstatic`
3. Configure web server to serve static files

## SSL/HTTPS
1. Obtain SSL certificate (AWS Certificate Manager)
2. Configure load balancer with SSL termination
3. Update `ALLOWED_HOSTS` and security settings

## Monitoring and Logging
1. Configure CloudWatch for application logs
2. Set up health checks
3. Configure alerts for errors and performance metrics

## Continuous Deployment
Set up GitLab CI/CD pipeline:
1. Create `.gitlab-ci.yml` file
2. Configure deployment stages
3. Set up environment variables in GitLab

## Testing Deployment
1. Verify all endpoints are accessible
2. Test assistant functionality: `POST /scrap/assistant/`
3. Check database connectivity
4. Verify environment variables are loaded correctly

## Troubleshooting
- Check application logs in CloudWatch
- Verify security group configurations
- Ensure all environment variables are set
- Check database connectivity
- Verify OpenAI API key is valid

## Support
For deployment issues, check:
1. AWS documentation
2. Django deployment guide
3. Application logs for specific errors
