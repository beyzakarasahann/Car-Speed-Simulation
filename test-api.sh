#!/bin/bash

# API Test Script for Car Speed Simulation
# =======================================

echo "🧪 Testing API Connectivity"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_api() {
    local url=$1
    local description=$2
    
    echo -n "Testing $description: "
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ SUCCESS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        return 1
    fi
}

# Test local development
echo ""
echo "🔧 Local Development Tests:"
echo "---------------------------"

# Check if backend is running
if pgrep -f "uvicorn.*8000" > /dev/null; then
    echo -e "${GREEN}✅ Backend is running on port 8000${NC}"
    
    # Test backend directly
    test_api "http://localhost:8000/" "Backend root endpoint"
    test_api "http://localhost:8000/health" "Backend health check"
    
    # Test API endpoints
    test_api "http://localhost:8000/api/" "Backend API root"
    
else
    echo -e "${RED}❌ Backend not running on port 8000${NC}"
    echo "Start backend with: cd backend && uvicorn app.main:app --reload --port 8000"
fi

# Check if frontend is running
if pgrep -f "next.*3000" > /dev/null; then
    echo -e "${GREEN}✅ Frontend is running on port 3000${NC}"
    
    # Test frontend
    test_api "http://localhost:3000/" "Frontend root"
    
    # Test frontend API proxy
    test_api "http://localhost:3000/api/" "Frontend API proxy"
    
else
    echo -e "${RED}❌ Frontend not running on port 3000${NC}"
    echo "Start frontend with: cd frontend && npm run dev"
fi

# Test production endpoints (if domain is configured)
echo ""
echo "🌐 Production Tests:"
echo "-------------------"

DOMAIN="speedsimulator.tech"

# Test HTTPS endpoints
test_api "https://$DOMAIN/" "Production frontend"
test_api "https://$DOMAIN/api/" "Production API"
test_api "https://$DOMAIN/health" "Production health check"

# Test specific API endpoints
echo ""
echo "🔍 API Endpoint Tests:"
echo "---------------------"

# Test auto-route endpoint
echo -n "Testing auto-route endpoint: "
if curl -s -X POST "https://$DOMAIN/api/auto-route" \
    -H "Content-Type: application/json" \
    -d '{"provider":"here","start":{"lat":41.015,"lon":29.01},"end":{"lat":41.016,"lon":29.011}}' \
    | grep -q "route\|error" 2>/dev/null; then
    echo -e "${GREEN}✅ SUCCESS${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
fi

# Test snap-to-road endpoint
echo -n "Testing snap-to-road endpoint: "
if curl -s -X POST "https://$DOMAIN/api/snap-to-road" \
    -H "Content-Type: application/json" \
    -d '{"point":{"lat":41.015,"lon":29.01}}' \
    | grep -q "lat\|error" 2>/dev/null; then
    echo -e "${GREEN}✅ SUCCESS${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
fi

echo ""
echo "📊 Summary:"
echo "----------"
echo "If all tests pass, your API is working correctly!"
echo "If some fail, check:"
echo "  1. Backend is running (uvicorn)"
echo "  2. Frontend is running (npm run dev)"
echo "  3. Nginx is configured correctly"
echo "  4. SSL certificate is valid"
echo "  5. Firewall allows ports 80, 443, 3000, 8000"






