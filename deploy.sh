#!/bin/bash

# Exit on any error
set -e

# Load environment variables from .env.dev
if [ -f .env.dev ]; then
    export $(grep -v '^#' .env.dev | grep -v '^$' | xargs)
else
    echo "Error: .env.dev file not found"
    exit 1
fi

# Required environment variables check
required_vars=(
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY" 
    "AWS_REGION"
    "AWS_ACCOUNT_ID"
    "ECR_REPOSITORY_NAME"
    "IMAGE_TAG"
    "LAMBDA_FUNCTION_NAME"
)

echo "Checking required environment variables..."
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env.dev"
        exit 1
    fi
done

echo "✓ All required environment variables are set"

# Set ECR repository URI
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID".dkr.ecr."$AWS_REGION".amazonaws.com

# Build Docker image for linux/arm64
echo "Building Docker image for linux/arm64..."
docker build -t "$ECR_URI:$IMAGE_TAG" --push .

# Image already pushed with --push flag above
echo "✓ Image pushed to ECR: $ECR_URI:$IMAGE_TAG"

# Update existing Lambda function
echo "Updating Lambda function: $LAMBDA_FUNCTION_NAME..."

# Update function code with new image
echo "Updating function code..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --image-uri "$ECR_URI:$IMAGE_TAG" \
    --region "$AWS_REGION"

# Update function configuration
echo "Updating function configuration..."
aws lambda update-function-configuration \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --architectures arm64 \
    --environment "Variables={
        S3_BUCKET_NAME=$S3_BUCKET_NAME,
        CRAWL4_AI_BASE_DIRECTORY=/tmp/crawl4ai
    }" \
    --region "$AWS_REGION"

echo "🎉 Lambda update completed successfully!"
echo "Function: $LAMBDA_FUNCTION_NAME"
echo "Image: $ECR_URI:$IMAGE_TAG"