#!/bin/bash

# Customer Loan Management App - Docker Deployment Script
echo "🏦 Customer Loan Management App v1.0"
echo "===================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Excel file exists
if [ ! -f "Customer_Loan_2025_06_07.xlsx" ]; then
    echo "⚠️  Excel file 'Customer_Loan_2025_06_07.xlsx' not found in current directory"
    echo "   Please place your Excel file in the same directory as this script"
    exit 1
fi

echo "✅ Excel file found"

# Check if Docker Compose is available
if command -v docker-compose &> /dev/null; then
    echo "🐳 Starting with Docker Compose..."
    docker-compose up --build
elif docker compose version &> /dev/null; then
    echo "🐳 Starting with Docker Compose (newer version)..."
    docker compose up --build
else
    echo "🐳 Starting with Docker..."
    
    # Build the image
    echo "🔨 Building Docker image..."
    docker build -t customer-loan-app .
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to build Docker image"
        exit 1
    fi
    
    echo "✅ Docker image built successfully"
    
    # Run the container
    echo "🚀 Starting application..."
    docker run -p 8501:8501 -v "$(pwd):/app/data" customer-loan-app
fi

echo "🎉 Application should be available at: http://localhost:8501"
