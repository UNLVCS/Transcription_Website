#!/bin/bash
#
# Meeting Minutes Generator - Deployment Script
# Run this on your server: bash deploy.sh
#

set -e  # Exit on error

echo "=========================================="
echo "  Meeting Minutes Generator - Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="$HOME/Transcription_Website"
REPO_URL="https://github.com/UNLVCS/Transcription_Website.git"
PORT=5000

# Step 1: Check system requirements
echo -e "\n${YELLOW}[1/7] Checking system requirements...${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python 3.9+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Check RAM
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [ "$RAM_GB" -lt 6 ]; then
    echo -e "${YELLOW}Warning: 8GB+ RAM recommended. Found: ${RAM_GB}GB${NC}"
else
    echo -e "${GREEN}✓ RAM: ${RAM_GB}GB${NC}"
fi

# Check disk space
DISK_FREE=$(df -BG ~ | awk 'NR==2 {print $4}' | tr -d 'G')
if [ "$DISK_FREE" -lt 10 ]; then
    echo -e "${RED}Error: 10GB+ free space required. Found: ${DISK_FREE}GB${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Disk space: ${DISK_FREE}GB free${NC}"

# Step 2: Install system dependencies
echo -e "\n${YELLOW}[2/7] Installing system dependencies...${NC}"

if command -v apt &> /dev/null; then
    sudo apt update
    sudo apt install -y python3-pip python3-venv ffmpeg git
elif command -v yum &> /dev/null; then
    sudo yum install -y python3-pip python3-virtualenv ffmpeg git
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3-pip python3-virtualenv ffmpeg git
else
    echo -e "${YELLOW}Warning: Could not detect package manager. Ensure ffmpeg and git are installed.${NC}"
fi

# Check ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ ffmpeg installed${NC}"

# Step 3: Clone or update repository
echo -e "\n${YELLOW}[3/7] Setting up application...${NC}"

if [ -d "$APP_DIR" ]; then
    echo "Updating existing installation..."
    cd "$APP_DIR"
    git pull origin main
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi
echo -e "${GREEN}✓ Repository ready${NC}"

# Step 4: Create virtual environment
echo -e "\n${YELLOW}[4/7] Setting up Python environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip --quiet

echo -e "${GREEN}✓ Virtual environment ready${NC}"

# Step 5: Install Python dependencies
echo -e "\n${YELLOW}[5/7] Installing Python dependencies (this may take 10-20 minutes)...${NC}"

# Install PyTorch CPU version
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet

# Install other dependencies
pip install -r requirements.txt --quiet

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 6: Configure environment
echo -e "\n${YELLOW}[6/7] Configuring environment...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    # Generate random secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/change-this-to-a-random-secret-key/$SECRET_KEY/" .env
    sed -i "s/FLASK_ENV=development/FLASK_ENV=production/" .env
    echo -e "${GREEN}✓ Environment configured${NC}"
else
    echo -e "${GREEN}✓ Environment file exists${NC}"
fi

# Step 7: Create systemd service
echo -e "\n${YELLOW}[7/7] Setting up systemd service...${NC}"

SERVICE_FILE="/etc/systemd/system/meeting-minutes.service"
VENV_PATH="$APP_DIR/venv"

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Meeting Minutes Generator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/gunicorn --workers 2 --threads 2 --timeout 7200 --bind 0.0.0.0:$PORT app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable meeting-minutes
sudo systemctl restart meeting-minutes

echo -e "${GREEN}✓ Service configured${NC}"

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo -e "${GREEN}  Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Website URL: http://$SERVER_IP:$PORT"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status meeting-minutes"
echo "  View logs:     sudo journalctl -u meeting-minutes -f"
echo "  Restart:       sudo systemctl restart meeting-minutes"
echo "  Stop:          sudo systemctl stop meeting-minutes"
echo ""
echo "Next steps:"
echo "  1. Open http://$SERVER_IP:$PORT in your browser"
echo "  2. Get HuggingFace token from: https://huggingface.co/settings/tokens"
echo "  3. Get Gemini API key from: https://aistudio.google.com/app/apikey"
echo "  4. Accept pyannote terms at: https://huggingface.co/pyannote/speaker-diarization-3.0"
echo ""
