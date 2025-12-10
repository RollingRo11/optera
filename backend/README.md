# MARA Resource Allocation Backend

AI-powered resource allocation system for the MARA hackathon using LangGraph agents.

## Features

- **LangGraph Agents**: Minimal implementation using LangGraph for resource allocation decisions
- **Cost Optimization**: Prioritizes cost efficiency while maintaining inference performance
- **Real-time Pricing**: Integrates with MARA API for live market data
- **Inference Priority**: Configurable priority weighting for inference vs mining workloads
- **Power Constraints**: Respects site power limits and validates allocations

## API Endpoints

### Core Endpoints

- `GET /status` - Get current site status and market prices
- `POST /allocate` - Optimize resource allocation using AI agent
- `POST /deploy` - Deploy allocation to MARA platform
- `GET /market-intelligence` - Get AI-powered market analysis

### Allocation Request

```json
{
  "target_revenue": 50000,
  "inference_priority": 0.8,
  "power_limit": 1000000
}
```

### Allocation Response

```json
{
  "allocation": {
    "air_miners": 0,
    "hydro_miners": 5,
    "immersion_miners": 10,
    "gpu_compute": 30,
    "asic_compute": 20
  },
  "expected_revenue": 45000.0,
  "expected_cost": 35000.0,
  "efficiency_score": 85.0,
  "reasoning": "Prioritized inference workloads based on current token prices..."
}
```

## Usage

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables in `.env`:
```
OPENAI_API_KEY=your_openai_key_here
MARA_API_KEY=your_mara_key_here
```

3. Start the server:
```bash
./start.sh
```

The API will be available at `http://localhost:8000`

## Architecture

- **FastAPI**: Web framework for API endpoints
- **LangGraph**: Agent workflow for resource allocation decisions
- **OpenAI GPT-4o**: LLM for market analysis and optimization
- **MARA Client**: Interface to MARA hackathon API

## Agent Workflow

1. **Fetch Data**: Retrieve current prices, inventory, and site status
2. **Analyze Market**: AI analysis of market conditions and trends
3. **Optimize Allocation**: Generate optimal resource allocation
4. **Validate**: Ensure allocation meets power and other constraints