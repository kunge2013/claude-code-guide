#!/bin/bash
# Startup script for LangChain ChatBI Web Interface

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  LangChain ChatBI Web Interface${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Set PYTHONPATH
export PYTHONPATH="/home/fk/workspace/github/claude_guide/simple-project/chatbi:$PYTHONPATH"

# Check for Flask
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Flask not installed. Installing...${NC}"
    pip install flask -q
fi

# Check for API key
if [ -z "$LLM_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  LLM_API_KEY not set. Using mock mode.${NC}"
    echo -e "${YELLOW}   To use real LLM, set: export LLM_API_KEY='your-api-key'${NC}"
    echo ""
    export LLM_API_KEY="mock-key-for-demo"
fi

echo -e "${GREEN}Starting web server...${NC}"
echo ""
echo "Web interface will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Flask app
cd /home/fk/workspace/github/claude_guide/simple-project/chatbi/langchain_chatbi
python web/app.py
