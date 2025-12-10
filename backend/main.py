from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from datetime import datetime
from dotenv import load_dotenv

from agents.simple_allocation_agent import SimpleAllocationAgent
from agents.chatbot_agent import ChatbotAgent
from utils.mara_client import MaraClient
from utils.btc_client import BTCClient

load_dotenv()

app = FastAPI(title="MARA Resource Allocation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mara_client = MaraClient(api_key=os.getenv("MARA_API_KEY"))
btc_client = BTCClient()
allocation_agent = SimpleAllocationAgent(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    mara_client=mara_client
)
chatbot_agent = ChatbotAgent(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    mara_client=mara_client,
    allocation_agent=allocation_agent
)

class AllocationRequest(BaseModel):
    target_revenue: Optional[float] = None
    inference_priority: float = 0.8  # 0-1 scale, higher = prioritize inference more
    power_limit: Optional[int] = None

class AllocationResponse(BaseModel):
    allocation: Dict[str, int]
    expected_revenue: float
    expected_cost: float
    efficiency_score: float
    reasoning: str

class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    context_used: Optional[Dict[str, Any]] = None
    error: bool = False

@app.get("/")
async def root():
    return {"message": "MARA Resource Allocation API"}

@app.get("/status")
async def get_status():
    """Get current site status from MARA API"""
    try:
        inventory = await mara_client.get_inventory()
        prices = await mara_client.get_current_prices()
        site_status = await mara_client.get_site_status()
        site_status = mara_client.apply_local_allocation(site_status, inventory, prices)
        btc_data = await btc_client.get_btc_data()
        return {
            "site_status": site_status,
            "current_prices": prices,
            "btc_data": btc_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/allocate", response_model=AllocationResponse)
async def optimize_allocation(request: AllocationRequest):
    """Optimize resource allocation using AI agent"""
    try:
        result = await allocation_agent.optimize_allocation(
            target_revenue=request.target_revenue,
            inference_priority=request.inference_priority,
            power_limit=request.power_limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deploy")
async def deploy_allocation(allocation: Dict[str, int]):
    """Deploy the optimized allocation to MARA"""
    try:
        result = await mara_client.update_allocation(allocation)
        return {"status": "deployed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-intelligence")
async def get_market_intelligence():
    """Get AI-powered market analysis and recommendations"""
    try:
        analysis = await allocation_agent.analyze_market_conditions()
        btc_data = await btc_client.get_btc_data()
        analysis["btc_data"] = btc_data
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/btc")
async def get_btc_data():
    """Get real-time Bitcoin data from Yahoo Finance"""
    try:
        btc_data = await btc_client.get_btc_data()
        return btc_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(chat_message: ChatMessage):
    """Chat with the AI assistant about system status and operations"""
    try:
        response = await chatbot_agent.process_user_message(
            message=chat_message.message,
            context=chat_message.context
        )
        return ChatResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/summary")
async def get_system_summary():
    """Get AI-generated system summary for dashboard"""
    try:
        summary = await chatbot_agent.get_system_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/history")
async def get_chat_history(limit: int = 10):
    """Get recent chat conversation history"""
    try:
        history = chatbot_agent.get_conversation_history(limit=limit)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/history")
async def clear_chat_history():
    """Clear chat conversation history"""
    try:
        chatbot_agent.clear_conversation_history()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/outputs")
async def get_agent_outputs():
    """Get recent outputs from all agents"""
    try:
        outputs = {
            "SimpleAllocationAgent": await get_allocation_agent_output(),
            "ChatbotAgent": await get_chatbot_agent_output(), 
            "MaraClient": await get_mara_client_output(),
            "BTCClient": await get_btc_client_output()
        }
        return outputs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Cache for agent outputs to avoid too frequent calls
_agent_output_cache = {}
_cache_timestamps = {}

async def get_allocation_agent_output():
    """Get recent allocation agent reasoning"""
    cache_key = "allocation_agent"
    now = datetime.now()
    
    # Return cached result if less than 30 seconds old
    if (cache_key in _cache_timestamps and 
        (now - _cache_timestamps[cache_key]).total_seconds() < 30):
        return _agent_output_cache[cache_key]
    
    try:
        # Get latest allocation decision (less frequently)
        result = await allocation_agent.optimize_allocation(inference_priority=0.7)
        output = {
            "timestamp": now.isoformat(),
            "output": f"Optimizing allocation: {result['reasoning'][:200]}...",
            "status": "active"
        }
    except Exception as e:
        output = {
            "timestamp": now.isoformat(),
            "output": f"Analyzing market conditions and power utilization patterns...",
            "status": "monitoring"
        }
    
    _agent_output_cache[cache_key] = output
    _cache_timestamps[cache_key] = now
    return output

async def get_chatbot_agent_output():
    """Get recent chatbot agent activity"""
    try:
        summary = await chatbot_agent.get_system_summary()
        return {
            "timestamp": datetime.now().isoformat(),
            "output": f"System health: operational. Processed {len(chatbot_agent.conversation_history)} recent conversations.",
            "status": "ready"
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "output": "Standing by for user interactions...",
            "status": "idle"
        }

async def get_mara_client_output():
    """Get recent MARA client activity"""
    try:
        site_status = await mara_client.get_site_status()
        prices = await mara_client.get_current_prices()
        return {
            "timestamp": datetime.now().isoformat(),
            "output": f"Live sync: {site_status['total_power_used']}W used, latest price: ${prices[0]['energy_price']:.3f}/kWh",
            "status": "syncing"
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "output": f"Connection issue: {str(e)[:100]}...",
            "status": "error"
        }

async def get_btc_client_output():
    """Get recent BTC client activity"""
    try:
        btc_data = await btc_client.get_btc_data()
        return {
            "timestamp": datetime.now().isoformat(),
            "output": f"BTC: ${btc_data['price']:,.0f} ({btc_data['change_percent']:+.1f}%) - Market data refreshed",
            "status": "updating"
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "output": "Fetching latest Bitcoin market data...",
            "status": "fetching"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)