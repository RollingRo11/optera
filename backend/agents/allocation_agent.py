from typing import Dict, Any, Optional, List, TypedDict
import json
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.mara_client import MaraClient

class AllocationState(TypedDict):
    current_prices: List[Dict[str, Any]]
    inventory: Dict[str, Any]
    site_status: Dict[str, Any]
    target_revenue: Optional[float]
    inference_priority: float
    power_limit: Optional[int]
    analysis: str
    allocation: Dict[str, int]
    reasoning: str
    efficiency_score: float

class AllocationAgent:
    def __init__(self, openai_api_key: str, mara_client: MaraClient):
        self.mara_client = mara_client
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.1
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for resource allocation"""
        graph = StateGraph(AllocationState)
        
        # Add nodes
        graph.add_node("fetch_data", self._fetch_market_data)
        graph.add_node("analyze_market", self._analyze_market_conditions)
        graph.add_node("optimize_allocation", self._optimize_allocation)
        graph.add_node("validate_allocation", self._validate_allocation)
        
        # Add edges
        graph.add_edge("fetch_data", "analyze_market")
        graph.add_edge("analyze_market", "optimize_allocation")
        graph.add_edge("optimize_allocation", "validate_allocation")
        graph.add_edge("validate_allocation", END)
        
        # Set entry point
        graph.set_entry_point("fetch_data")
        
        return graph.compile()
    
    async def _fetch_market_data(self, state: AllocationState) -> AllocationState:
        """Fetch current market data from MARA API"""
        try:
            state["current_prices"] = await self.mara_client.get_current_prices()
            state["inventory"] = await self.mara_client.get_inventory()
            state["site_status"] = await self.mara_client.get_site_status()
        except Exception as e:
            print(f"Error fetching market data: {e}")
        
        return state
    
    async def _analyze_market_conditions(self, state: AllocationState) -> AllocationState:
        """Analyze current market conditions using AI"""
        system_prompt = """You are a resource allocation analyst for a mining and compute operation. 
        Analyze the current market conditions and provide insights for optimal resource allocation.
        Focus on cost efficiency while prioritizing inference workloads as requested."""
        
        human_prompt = f"""
        Current Market Data:
        - Prices: {json.dumps(state["current_prices"][:3], indent=2)}
        - Inventory: {json.dumps(state["inventory"], indent=2)}
        - Site Status: {json.dumps(state["site_status"], indent=2)}
        - Inference Priority: {state["inference_priority"]}
        
        Analyze these conditions and recommend an allocation strategy. Consider:
        1. Current price trends for energy, hash rate, and token inference
        2. Revenue potential of each resource type
        3. Cost efficiency ratios
        4. Inference priority weighting (higher = more focus on inference)
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        state["analysis"] = response.content
        
        return state
    
    async def _optimize_allocation(self, state: AllocationState) -> AllocationState:
        """Generate optimal resource allocation using AI"""
        system_prompt = """You are an optimization engine for resource allocation. Based on the market analysis, 
        generate an optimal allocation of mining and compute resources. Return your response as a JSON object with:
        
        {
            "allocation": {
                "air_miners": <number>,
                "hydro_miners": <number>, 
                "immersion_miners": <number>,
                "gpu_compute": <number>,
                "asic_compute": <number>
            },
            "reasoning": "<explanation of allocation decisions>",
            "efficiency_score": <0-100 score>
        }
        
        Constraints:
        - Total power usage cannot exceed site power limit
        - Prioritize inference workloads based on inference_priority setting
        - Optimize for cost efficiency and revenue generation
        """
        
        # Calculate available power
        site_power = state["site_status"].get("power", {})
        total_power_limit = state["power_limit"] or 1000000  # Default from API docs
        
        human_prompt = f"""
        Market Analysis: {state["analysis"]}
        
        Power Constraints:
        - Total Power Limit: {total_power_limit}
        - Current Power Usage: {state["site_status"].get('total_power_used', 0)}
        
        Optimization Parameters:
        - Target Revenue: {state["target_revenue"] or 'maximize'}
        - Inference Priority: {state["inference_priority"]} (0=mining focus, 1=inference focus)
        
        Generate the optimal allocation considering these factors. Ensure the allocation doesn't exceed power limits.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract JSON from response
            response_text = response.content
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object in the response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_text = response_text[start:end]
            
            result = json.loads(json_text)
            state["allocation"] = result.get("allocation", {})
            state["reasoning"] = result.get("reasoning", "No reasoning provided")
            state["efficiency_score"] = result.get("efficiency_score", 0.0)
            
        except Exception as e:
            print(f"Error parsing optimization response: {e}")
            # Fallback allocation prioritizing inference
            state["allocation"] = {
                "air_miners": 0,
                "hydro_miners": 5,
                "immersion_miners": 10,
                "gpu_compute": 30,
                "asic_compute": 20
            }
            state["reasoning"] = "Fallback allocation due to parsing error"
            state["efficiency_score"] = 50.0
        
        return state
    
    async def _validate_allocation(self, state: AllocationState) -> AllocationState:
        """Validate the proposed allocation against constraints"""
        # Check power constraints
        power_usage = self.mara_client.calculate_power_usage(state["allocation"], state["inventory"])
        power_limit = state["power_limit"] or 1000000
        
        if power_usage > power_limit:
            # Scale down allocation proportionally
            scale_factor = power_limit / power_usage
            for key in state["allocation"]:
                state["allocation"][key] = int(state["allocation"][key] * scale_factor)
            
            state["reasoning"] += f" (Scaled down by {scale_factor:.2f} to meet power constraints)"
        
        return state
    
    async def optimize_allocation(
        self, 
        target_revenue: Optional[float] = None,
        inference_priority: float = 0.8,
        power_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Main entry point for allocation optimization"""
        initial_state: AllocationState = {
            "current_prices": [],
            "inventory": {},
            "site_status": {},
            "target_revenue": target_revenue,
            "inference_priority": inference_priority,
            "power_limit": power_limit,
            "analysis": "",
            "allocation": {},
            "reasoning": "",
            "efficiency_score": 0.0
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        # Calculate expected revenue and cost
        revenue_breakdown = self.mara_client.calculate_expected_revenue(
            final_state["allocation"], 
            final_state["inventory"], 
            final_state["current_prices"]
        )
        
        power_usage = self.mara_client.calculate_power_usage(
            final_state["allocation"], 
            final_state["inventory"]
        )
        
        # Estimate cost (simplified - energy price * power usage)
        if final_state["current_prices"]:
            energy_price = final_state["current_prices"][0].get("energy_price", 0)
            expected_cost = power_usage * energy_price
        else:
            expected_cost = 0
        
        return {
            "allocation": final_state["allocation"],
            "expected_revenue": revenue_breakdown["total"],
            "expected_cost": expected_cost,
            "efficiency_score": final_state["efficiency_score"],
            "reasoning": final_state["reasoning"]
        }
    
    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """Standalone market analysis"""
        try:
            prices = await self.mara_client.get_current_prices()
            inventory = await self.mara_client.get_inventory()
            
            system_prompt = """You are a market intelligence analyst. Provide actionable insights 
            about current market conditions for mining and inference operations."""
            
            human_prompt = f"""
            Current Market Data:
            - Prices: {json.dumps(prices[:5], indent=2)}
            - Available Inventory: {json.dumps(inventory, indent=2)}
            
            Provide analysis including:
            1. Price trend analysis
            2. Optimal resource type recommendations
            3. Risk assessment
            4. Market timing insights
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            return {
                "analysis": response.content,
                "current_prices": prices,
                "inventory": inventory,
                "timestamp": prices[0].get("timestamp") if prices else None
            }
            
        except Exception as e:
            return {"error": str(e)}