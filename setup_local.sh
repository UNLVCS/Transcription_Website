#!/bin/bash

# Local Testing Script for Meeting Minutes Generator
# This script helps you test the application locally before deploying to production

echo "=================================="
echo "Meeting Minutes - Local Test Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi
echo "✅ Python is installed"
echo ""

# Check PostgreSQL
echo "Checking PostgreSQL..."
which psql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL is installed"
else
    echo "⚠️  PostgreSQL not found. Install with: sudo apt install postgresql"
fi
echo ""

# Check ffmpeg
echo "Checking ffmpeg..."
which ffmpeg > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ ffmpeg is installed"
else
    echo "❌ ffmpeg not found. Install with: sudo apt install ffmpeg"
    exit 1
fi
echo ""

# Create virtual environment
echo "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies (this may take 10-20 minutes)..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo ""

# Setup environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    
    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Update .env with generated key
    sed -i "s/your-super-secret-key-change-this-in-production/$SECRET_KEY/" .env
    
    echo "✅ .env file created with random secret key"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and update DATABASE_URL with your PostgreSQL credentials"
    echo "   Example: postgresql://username:password@localhost:5432/meeting_minutes"
    echo ""
    read -p "Press Enter after you've updated .env file..."
else
    echo "✅ .env file already exists"
fi
echo ""

# Initialize database
echo "Initializing database..."
python3 -c "from app import init_db; init_db()" 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database initialized successfully"
else
    echo "❌ Failed to initialize database"
    echo "   Make sure PostgreSQL is running and credentials in .env are correct"
    echo "   Run: sudo systemctl status postgresql"
    exit 1
fi
echo ""

echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "To start the application in development mode:"
echo "  1. source venv/bin/activate"
echo "  2. python3 app.py"
echo ""
echo "To start the application in production mode:"
echo "  1. source venv/bin/activate"
echo "  2. gunicorn --workers 4 --bind 0.0.0.0:5000 app:app"
echo ""
echo "Then open: http://localhost:5000"
echo ""
echo "Before using the application, users need:"
echo "  - HuggingFace Token: https://huggingface.co/settings/tokens"
echo "  - Gemini API Key: https://aistudio.google.com/app/apikey"
echo ""
