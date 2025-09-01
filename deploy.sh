#!/bin/bash

# Car Speed Simulation - Production Deployment Script
# =================================================

set -e  # Exit on any error

echo "🚀 Car Speed Simulation Production Deployment"
echo "============================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   exit 1
fi

# Configuration
DOMAIN="speedsimulator.tech"
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN"
NGINX_ENABLED="/etc/nginx/sites-enabled/$DOMAIN"

echo "📋 Configuration:"
echo "  Domain: $DOMAIN"
echo "  Backend Port: $BACKEND_PORT"
echo "  Frontend Port: $FRONTEND_PORT"

# 1. Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y nginx certbot python3-certbot-nginx nodejs npm python3-pip python3-venv

# 3. Setup project directory
echo "📁 Setting up project directory..."
PROJECT_DIR="/var/www/speedsimulator"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# 4. Copy project files
echo "📋 Copying project files..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# 5. Setup backend
echo "🐍 Setting up Python backend..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Setup frontend
echo "⚛️ Setting up Node.js frontend..."
cd frontend
npm ci --production
npm run build
cd ..

# 7. Setup C++ physics engine (if CMake available)
if command -v cmake &> /dev/null; then
    echo "🔨 Building C++ physics engine..."
    cd backend/cpp
    mkdir -p build
    cd build
    cmake ..
    make
    cd ../../..
else
    echo "⚠️ CMake not found, skipping C++ physics engine build"
fi

# 8. Setup Nginx
echo "🌐 Setting up Nginx..."
sudo cp nginx.conf $NGINX_CONFIG
sudo ln -sf $NGINX_CONFIG $NGINX_ENABLED
sudo nginx -t
sudo systemctl reload nginx

# 9. Setup SSL certificate
echo "🔒 Setting up SSL certificate..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# 10. Create systemd services
echo "⚙️ Creating systemd services..."

# Backend service
sudo tee /etc/systemd/system/speedsim-backend.service > /dev/null <<EOF
[Unit]
Description=Car Speed Simulation Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR/backend
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Frontend service
sudo tee /etc/systemd/system/speedsim-frontend.service > /dev/null <<EOF
[Unit]
Description=Car Speed Simulation Frontend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR/frontend
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 11. Enable and start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable speedsim-backend
sudo systemctl enable speedsim-frontend
sudo systemctl start speedsim-backend
sudo systemctl start speedsim-frontend

# 12. Final checks
echo "✅ Final checks..."
sleep 5

# Check if services are running
if sudo systemctl is-active --quiet speedsim-backend; then
    echo "✅ Backend service is running"
else
    echo "❌ Backend service failed to start"
    sudo systemctl status speedsim-backend
fi

if sudo systemctl is-active --quiet speedsim-frontend; then
    echo "✅ Frontend service is running"
else
    echo "❌ Frontend service failed to start"
    sudo systemctl status speedsim-frontend
fi

# Test API endpoint
echo "🔍 Testing API endpoint..."
if curl -s -f "https://$DOMAIN/api/" > /dev/null; then
    echo "✅ API endpoint is accessible"
else
    echo "❌ API endpoint test failed"
fi

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "🌐 Frontend: https://$DOMAIN"
echo "🔧 Backend API: https://$DOMAIN/api/"
echo "📊 API Docs: https://$DOMAIN/api/docs"
echo ""
echo "📋 Useful commands:"
echo "  View logs: sudo journalctl -u speedsim-backend -f"
echo "  Restart services: sudo systemctl restart speedsim-backend speedsim-frontend"
echo "  Check status: sudo systemctl status speedsim-backend speedsim-frontend"
echo ""


