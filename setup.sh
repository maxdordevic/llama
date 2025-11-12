#!/bin/bash
# Manus AI Clone - Quick Setup Script
# Automatically sets up and tests the system

set -e  # Exit on error

echo "========================================"
echo "🚀 MANUS AI CLONE - QUICK SETUP"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
python3 --version || {
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
}
echo -e "${GREEN}✓ Python 3 available${NC}"
echo ""

# Check if .env exists
echo "📋 Checking configuration..."
if [ -f "manus_ai/.env" ]; then
    echo -e "${GREEN}✓ Configuration file found${NC}"

    # Check for API keys
    if grep -q "GEMINI_API_KEY=.*[^_]" manus_ai/.env; then
        echo -e "${GREEN}✓ Gemini API key configured${NC}"
    else
        echo -e "${YELLOW}⚠ Gemini API key not set${NC}"
    fi

    if grep -q "PERPLEXITY_API_KEY=.*[^_]" manus_ai/.env; then
        echo -e "${GREEN}✓ Perplexity API key configured${NC}"
    else
        echo -e "${YELLOW}⚠ Perplexity API key not set${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No .env file found, creating from example...${NC}"
    cp manus_ai/.env.example manus_ai/.env
    echo -e "${YELLOW}⚠ Please edit manus_ai/.env and add your API keys${NC}"
fi
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
echo "This may take a few minutes..."
echo ""

pip3 install -q python-dotenv aiohttp google-generativeai 2>&1 | tail -5

echo -e "${GREEN}✓ Core dependencies installed${NC}"
echo ""

# Optional: Install all dependencies
read -p "Install all dependencies (for full functionality)? [y/N]: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing full dependencies..."
    pip3 install -q -r manus_ai/requirements.txt 2>&1 | tail -10
    echo -e "${GREEN}✓ All dependencies installed${NC}"
fi
echo ""

# Run tests
echo "🧪 Running connectivity tests..."
echo ""

python3 test_dual_providers.py || {
    echo -e "${YELLOW}⚠ Provider test had issues. Check API keys and network.${NC}"
}
echo ""

# Show quick start
echo "========================================"
echo "✅ SETUP COMPLETE!"
echo "========================================"
echo ""
echo "🚀 Quick Start:"
echo ""
echo "1. Start with Docker (recommended):"
echo "   docker-compose up -d"
echo ""
echo "2. Or start manually:"
echo "   Terminal 1: cd manus_ai && uvicorn manus_ai.api.main:app --reload"
echo "   Terminal 2: cd frontend && npm install && npm run dev"
echo ""
echo "3. Access the system:"
echo "   Frontend: http://localhost:3000"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "4. Run examples:"
echo "   python3 examples.py"
echo ""
echo "📚 Documentation:"
echo "   • QUICKSTART.md - 5-minute guide"
echo "   • PROVIDER_GUIDE.md - LLM provider details"
echo "   • MANUS_AI_README.md - Complete documentation"
echo ""
echo "🎉 Your Manus AI Clone is ready to use!"
echo ""
