from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.mara_client import MaraClient

class SimpleAllocationAgent:
    def __init__(self, openai_api_key: str, mara_client: MaraClient):
        self.mara_client = mara_client
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.1
        )
    
    async def optimize_allocation(
        self, 
        target_revenue: Optional[float] = None,
        inference_priority: float = 0.7,  # Default to 70%
        power_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Main entry point for allocation optimization"""
        
        try:
            # Step 1: Fetch market data
            current_prices = await self.mara_client.get_current_prices()
            inventory = await self.mara_client.get_inventory()
            site_status = await self.mara_client.get_site_status()
            
            # Step 2: Analyze market conditions
            analysis = await self._analyze_market_conditions(
                current_prices, inventory, site_status, inference_priority
            )
            
            # Step 3: Generate optimal allocation
            allocation_result = await self._generate_allocation(
                analysis, current_prices, inventory, site_status,
                target_revenue, inference_priority, power_limit
            )
            
            # Step 4: Validate and calculate metrics
            allocation = allocation_result["allocation"]
            reasoning = allocation_result["reasoning"]
            
            # Validate power constraints
            power_usage = self.mara_client.calculate_power_usage(allocation, inventory)
            actual_power_limit = power_limit or 1000000
            
            if power_usage > actual_power_limit:
                scale_factor = actual_power_limit / power_usage
                for key in allocation:
                    allocation[key] = int(allocation[key] * scale_factor)
                reasoning += f" (Scaled down by {scale_factor:.2f} to meet power constraints)"
            
            # Calculate expected revenue and cost
            revenue_breakdown = self.mara_client.calculate_expected_revenue(
                allocation, inventory, current_prices
            )
            
            if current_prices:
                energy_price = current_prices[0].get("energy_price", 0)
                expected_cost = power_usage * energy_price
            else:
                expected_cost = 0
            
            # Calculate efficiency score
            if expected_cost > 0:
                efficiency_score = min(100, (revenue_breakdown["total"] / expected_cost) * 20)
            else:
                efficiency_score = 50.0
            
            return {
                "allocation": allocation,
                "expected_revenue": revenue_breakdown["total"],
                "expected_cost": expected_cost,
                "efficiency_score": efficiency_score,
                "reasoning": reasoning
            }
            
        except Exception as e:
            # Fallback allocation
            return {
                "allocation": {
                    "air_miners": 0,
                    "hydro_miners": 5,
                    "immersion_miners": 10,
                    "gpu_compute": 30,
                    "asic_compute": 20
                },
                "expected_revenue": 45000.0,
                "expected_cost": 35000.0,
                "efficiency_score": 75.0,
                "reasoning": f"Fallback allocation due to error: {str(e)}"
            }
    
    async def _analyze_market_conditions(
        self, 
        current_prices: List[Dict[str, Any]], 
        inventory: Dict[str, Any], 
        site_status: Dict[str, Any],
        inference_priority: float
    ) -> str:
        """Analyze current market conditions using AI"""
        
        system_prompt = """You are a resource allocation analyst for a mining and compute operation. 
        Analyze the current market conditions and provide insights for optimal resource allocation.
        Focus on cost efficiency while prioritizing inference workloads as requested."""
        
        human_prompt = f"""
        Current Market Data:
        - Prices: {json.dumps(current_prices[:3], indent=2)}
        - Inventory: {json.dumps(inventory, indent=2)}
        - Site Status: {json.dumps(site_status, indent=2)}
        - Inference Priority: {inference_priority}
        
        Analyze these conditions and recommend an allocation strategy. Consider:
        1. Current price trends for energy, hash rate, and token inference
        2. Revenue potential of each resource type
        3. Cost efficiency ratios
        4. Inference priority weighting (higher = more focus on inference)
        
        Provide a concise analysis in 2-3 paragraphs.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def _generate_allocation(
        self,
        analysis: str,
        current_prices: List[Dict[str, Any]],
        inventory: Dict[str, Any],
        site_status: Dict[str, Any],
        target_revenue: Optional[float],
        inference_priority: float,
        power_limit: Optional[int]
    ) -> Dict[str, Any]:
        """Generate optimal resource allocation using AI"""
        
        system_prompt = """You are an optimization engine for resource allocation. Your PRIMARY GOAL is to MAXIMIZE REVENUE.
        Generate an optimal allocation of mining and compute resources that produces the highest possible revenue.
        
        Return your response as a JSON object with:
        {
            "allocation": {
                "air_miners": <number>,
                "hydro_miners": <number>, 
                "immersion_miners": <number>,
                "gpu_compute": <number>,
                "asic_compute": <number>
            },
            "reasoning": "<explanation of allocation decisions>"
        }
        
        Constraints:
        - Total power usage cannot exceed site power limit
        - Maintain 70% inference priority (favor compute over mining when possible)
        - PRIMARY OBJECTIVE: Maximize total revenue above all else
        """
        
        total_power_limit = power_limit or 1000000
        
        human_prompt = f"""
        Market Analysis: {analysis}
        
        Power Constraints:
        - Total Power Limit: {total_power_limit}W
        - Current Power Usage: {site_status.get('total_power_used', 0)}W
        
        REVENUE MAXIMIZATION PARAMETERS:
        - PRIMARY GOAL: MAXIMIZE TOTAL REVENUE (this is most important)
        - Inference Priority: 70% (favor compute over mining when revenue is similar)
        - Current Market Prices: Hash=${current_prices[0].get('hash_price', 0):.2f}, Token=${current_prices[0].get('token_price', 0):.2f}, Energy=${current_prices[0].get('energy_price', 0):.3f}
        
        Calculate the allocation that produces the HIGHEST total revenue possible within power constraints.
        Focus on the most profitable resource types given current market prices.
        Return only the JSON object, no additional text.
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
            return {
                "allocation": result.get("allocation", {}),
                "reasoning": result.get("reasoning", "No reasoning provided")
            }
            
        except Exception as e:
            print(f"Error parsing optimization response: {e}")
            # Fallback allocation prioritizing inference
            return {
                "allocation": {
                    "air_miners": 0,
                    "hydro_miners": 5,
                    "immersion_miners": 10,
                    "gpu_compute": 30,
                    "asic_compute": 20
                },
                "reasoning": "Fallback allocation due to parsing error"
            }
    
    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """Standalone market analysis"""
        try:
            prices = await self.mara_client.get_current_prices()
            inventory = await self.mara_client.get_inventory()
            
            analysis = await self._analyze_market_conditions(prices, inventory, {}, 0.8)
            
            return {
                "analysis": analysis,
                "current_prices": prices,
                "inventory": inventory,
                "timestamp": prices[0].get("timestamp") if prices else None
            }
            
        except Exception as e:
            return {"error": str(e)}