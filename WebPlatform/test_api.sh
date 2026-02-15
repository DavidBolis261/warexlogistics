#!/bin/bash

# API Testing Script for Sydney Metro Courier Driver API
# Usage: ./test_api.sh <API_URL>
# Example: ./test_api.sh https://driver-api-production.up.railway.app

API_URL="${1:-http://localhost:5000}"

echo "=========================================="
echo "Testing Sydney Metro Courier Driver API"
echo "API URL: $API_URL"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "✅ Test 1: Health Check"
curl -s "$API_URL/health" | python3 -m json.tool
echo ""
echo ""

# Test 2: API Documentation
echo "📚 Test 2: API Documentation"
curl -s "$API_URL/api/driver/docs" | python3 -m json.tool | head -20
echo ""
echo ""

# Test 3: Login (will fail without valid driver, but tests endpoint)
echo "🔐 Test 3: Login Endpoint"
echo "Testing with phone: 0412345678"
curl -s -X POST "$API_URL/api/driver/login" \
  -H "Content-Type: application/json" \
  -d '{"phone": "0412345678"}' | python3 -m json.tool
echo ""
echo ""

echo "=========================================="
echo "✅ Basic API tests complete!"
echo ""
echo "Next steps:"
echo "1. Create a driver in the dashboard with phone: 0412345678"
echo "2. Re-run this script to test login"
echo "3. Update iOS app APIService.swift with: $API_URL"
echo "=========================================="
