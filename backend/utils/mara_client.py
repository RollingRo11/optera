import httpx
from typing import Dict, List, Any, Optional
import asyncio

class MaraClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://mara-hackathon-api.onrender.com"
        self.headers = {"X-Api-Key": api_key}
        self._current_allocation: Optional[Dict[str, int]] = None
    
    async def get_current_prices(self) -> List[Dict[str, Any]]:
        """Get current pricing data from MARA API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/prices")
            response.raise_for_status()
            return response.json()
    
    async def get_inventory(self) -> Dict[str, Any]:
        """Get available inventory from MARA API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/inventory")
            response.raise_for_status()
            return response.json()
    
    async def get_site_status(self) -> Dict[str, Any]:
        """Get current site status and allocation"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/machines", headers=self.headers)
            response.raise_for_status()
            site_status = response.json()
            if self._current_allocation is None:
                self._current_allocation = {
                    "air_miners": site_status.get("air_miners", 0),
                    "hydro_miners": site_status.get("hydro_miners", 0),
                    "immersion_miners": site_status.get("immersion_miners", 0),
                    "gpu_compute": site_status.get("gpu_compute", 0),
                    "asic_compute": site_status.get("asic_compute", 0),
                }
            return site_status
    
    async def update_allocation(self, allocation: Dict[str, int]) -> Dict[str, Any]:
        """Update machine allocation on MARA"""
        # Map our internal names to MARA API names
        mara_allocation = {
            "air_miners": allocation.get("air_miners", 0),
            "hydro_miners": allocation.get("hydro_miners", 0),
            "immersion_miners": allocation.get("immersion_miners", 0),
            "gpu_compute": allocation.get("gpu_compute", 0),
            "asic_compute": allocation.get("asic_compute", 0),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/machines",
                headers=self.headers,
                json=mara_allocation
            )
            response.raise_for_status()
            self._current_allocation = mara_allocation
            return response.json()
    
    def get_local_allocation(self) -> Optional[Dict[str, int]]:
        return self._current_allocation
    
    def apply_local_allocation(
        self,
        site_status: Dict[str, Any],
        inventory: Dict[str, Any],
        prices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not self._current_allocation:
            return site_status
        
        adjusted = dict(site_status)
        allocation = self._current_allocation
        
        # Override unit counts
        adjusted["air_miners"] = allocation.get("air_miners", 0)
        adjusted["hydro_miners"] = allocation.get("hydro_miners", 0)
        adjusted["immersion_miners"] = allocation.get("immersion_miners", 0)
        adjusted["gpu_compute"] = allocation.get("gpu_compute", 0)
        adjusted["asic_compute"] = allocation.get("asic_compute", 0)
        
        # Power usage by category
        miners = inventory.get("miners", {})
        inference = inventory.get("inference", {})
        
        power_breakdown = {
            "air_miners": allocation.get("air_miners", 0) * miners.get("air", {}).get("power", 0),
            "hydro_miners": allocation.get("hydro_miners", 0) * miners.get("hydro", {}).get("power", 0),
            "immersion_miners": allocation.get("immersion_miners", 0) * miners.get("immersion", {}).get("power", 0),
            "gpu_compute": allocation.get("gpu_compute", 0) * inference.get("gpu", {}).get("power", 0),
            "asic_compute": allocation.get("asic_compute", 0) * inference.get("asic", {}).get("power", 0),
        }
        total_power_used = sum(power_breakdown.values())
        adjusted["power"] = power_breakdown
        adjusted["total_power_used"] = total_power_used
        
        # Revenue breakdown
        latest_prices = prices[0] if prices else {}
        hash_price = latest_prices.get("hash_price", 0)
        token_price = latest_prices.get("token_price", 0)
        
        revenue_breakdown = {
            "air_miners": allocation.get("air_miners", 0) * miners.get("air", {}).get("hashrate", 0) * hash_price,
            "hydro_miners": allocation.get("hydro_miners", 0) * miners.get("hydro", {}).get("hashrate", 0) * hash_price,
            "immersion_miners": allocation.get("immersion_miners", 0) * miners.get("immersion", {}).get("hashrate", 0) * hash_price,
            "gpu_compute": allocation.get("gpu_compute", 0) * inference.get("gpu", {}).get("tokens", 0) * token_price,
            "asic_compute": allocation.get("asic_compute", 0) * inference.get("asic", {}).get("tokens", 0) * token_price,
        }
        adjusted["revenue"] = revenue_breakdown
        adjusted["total_revenue"] = sum(revenue_breakdown.values())
        
        energy_price = latest_prices.get("energy_price", 0)
        adjusted["total_power_cost"] = total_power_used * energy_price
        
        return adjusted
    
    def calculate_power_usage(self, allocation: Dict[str, int], inventory: Dict[str, Any]) -> int:
        """Calculate total power usage for an allocation"""
        power_usage = 0
        
        # Mining power usage
        miners = inventory.get("miners", {})
        power_usage += allocation.get("air_miners", 0) * miners.get("air", {}).get("power", 0)
        power_usage += allocation.get("hydro_miners", 0) * miners.get("hydro", {}).get("power", 0)
        power_usage += allocation.get("immersion_miners", 0) * miners.get("immersion", {}).get("power", 0)
        
        # Inference power usage
        inference = inventory.get("inference", {})
        power_usage += allocation.get("gpu_compute", 0) * inference.get("gpu", {}).get("power", 0)
        power_usage += allocation.get("asic_compute", 0) * inference.get("asic", {}).get("power", 0)
        
        return power_usage
    
    def calculate_expected_revenue(
        self, 
        allocation: Dict[str, int], 
        inventory: Dict[str, Any], 
        prices: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate expected revenue for an allocation"""
        if not prices:
            return {"total": 0.0, "mining": 0.0, "inference": 0.0}
        
        # Use latest prices
        latest_prices = prices[0]
        
        mining_revenue = 0.0
        inference_revenue = 0.0
        
        # Mining revenue (hashrate * hash_price)
        miners = inventory.get("miners", {})
        mining_revenue += (
            allocation.get("air_miners", 0) * miners.get("air", {}).get("hashrate", 0) * 
            latest_prices.get("hash_price", 0)
        )
        mining_revenue += (
            allocation.get("hydro_miners", 0) * miners.get("hydro", {}).get("hashrate", 0) * 
            latest_prices.get("hash_price", 0)
        )
        mining_revenue += (
            allocation.get("immersion_miners", 0) * miners.get("immersion", {}).get("hashrate", 0) * 
            latest_prices.get("hash_price", 0)
        )
        
        # Inference revenue (tokens * token_price)
        inference = inventory.get("inference", {})
        inference_revenue += (
            allocation.get("gpu_compute", 0) * inference.get("gpu", {}).get("tokens", 0) * 
            latest_prices.get("token_price", 0)
        )
        inference_revenue += (
            allocation.get("asic_compute", 0) * inference.get("asic", {}).get("tokens", 0) * 
            latest_prices.get("token_price", 0)
        )
        
        return {
            "total": mining_revenue + inference_revenue,
            "mining": mining_revenue,
            "inference": inference_revenue
        }