#!/bin/bash

# Car Speed Simulation - Complete Setup Script
# ===========================================

echo "🚗 Car Speed Simulation Setup Starting..."
echo "========================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Python and Node.js found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Check if CMake is available for C++ physics engine
if command -v cmake &> /dev/null; then
    echo "🔨 Building C++ physics engine..."
    cd backend/cpp
    mkdir -p build
    cd build
    cmake ..
    make
    cd ../../..
    echo "✅ C++ physics engine built successfully"
else
    echo "⚠️  CMake not found. C++ physics engine will not be built."
    echo "   Install CMake to enable C++ physics engine features."
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "To start the backend:"
echo "  source venv/bin/activate"
echo "  cd backend"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Backend will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:3000"
echo ""


