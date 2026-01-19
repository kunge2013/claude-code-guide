#!/bin/bash
# LangChain ChatBI Demo Runner

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set PYTHONPATH
export PYTHONPATH="/home/fk/workspace/github/claude_guide/simple-project/chatbi:$PYTHONPATH"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  LangChain ChatBI Demo Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for API key
if [ -z "$LLM_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  LLM_API_KEY not set. Using mock mode.${NC}"
    echo -e "${YELLOW}   To use real LLM, set: export LLM_API_KEY='your-api-key'${NC}"
    echo ""
    export LLM_API_KEY="mock-key-for-demo"
fi

# Run verification
echo -e "${GREEN}=== Verifying Imports ===${NC}"
python -c "
from langchain_chatbi.agents import IntentClassificationAgent, SchemaAgent, SqlAgent
from langchain_chatbi.agents import QueryReasoningAgent, ChartGenerationAgent
from langchain_chatbi.agents import DiagnosisAgent, AnswerSummarizationAgent
from langchain_chatbi.llm import create_langchain_llm
from langchain_chatbi.graph import create_chatbi_graph
print('✓ All imports successful!')
print()
"

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Import failed. Please install dependencies:${NC}"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Run tests
echo -e "${GREEN}=== Running Unit Tests ===${NC}"
pytest tests/test_agents.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|passed|failed|warnings)"
echo ""

# Run demo
echo -e "${GREEN}=== Running Agent Demo ===${NC}"
python -c "
import asyncio
import os
from langchain_chatbi import (
    IntentClassificationAgent,
    SchemaAgent,
    SqlAgent,
    QueryReasoningAgent,
    ChartGenerationAgent,
    DiagnosisAgent,
    AnswerSummarizationAgent,
    create_langchain_llm,
    create_chatbi_graph,
)

async def demo():
    llm = create_langchain_llm()
    agents = [
        ('IntentClassificationAgent', IntentClassificationAgent(llm=llm)),
        ('SchemaAgent', SchemaAgent(llm=llm)),
        ('SqlAgent', SqlAgent(llm=llm)),
        ('QueryReasoningAgent', QueryReasoningAgent(llm=llm)),
        ('ChartGenerationAgent', ChartGenerationAgent(llm=llm)),
        ('DiagnosisAgent', DiagnosisAgent(llm=llm)),
        ('AnswerSummarizationAgent', AnswerSummarizationAgent(llm=llm)),
    ]

    print('Created agents:')
    for name, _ in agents:
        print(f'  ✓ {name}')

    print()
    graph = create_chatbi_graph()
    print(f'✓ LangGraph workflow compiled')
    print(f'  Nodes: {list(graph.nodes.keys())}')
    print()
    print('Demo completed successfully!')

asyncio.run(demo())
" 2>&1 | grep -v "DEBUG\|INFO\|WARNING"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Demo completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "To run individual demos:"
echo "  python demos/demo_intent_agent.py"
echo "  python demos/demo_streaming_agents.py"
echo "  python demos/demo_full_workflow.py"
