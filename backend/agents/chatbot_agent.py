from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class ChatbotAgent:
    """Subagent for user-facing question answering and system summarization"""
    
    def __init__(self, openai_api_key: str, mara_client, allocation_agent):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.3
        )
        self.mara_client = mara_client
        self.allocation_agent = allocation_agent
        self.conversation_history: List[Dict[str, str]] = []
        
    async def process_user_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user message and return AI response with context"""
        try:
            # Get current system state
            system_context = await self._get_system_context()
            
            # Build conversation context
            conversation_context = self._build_conversation_context(message, system_context, context)
            
            # Generate AI response
            response = await self._generate_response(conversation_context)
            
            # Store conversation
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "ai_response": response,
                "system_context": system_context
            })
            
            # Keep only last 10 conversations
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return {
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "context_used": system_context
            }
            
        except Exception as e:
            return {
                "response": f"I'm sorry, I encountered an error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": True
            }
    
    async def _get_system_context(self) -> Dict[str, Any]:
        """Gather current system state and recent activities"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "mara_status": None,
            "btc_data": None,
            "recent_allocations": [],
            "system_health": "unknown"
        }
        
        try:
            # Get MARA site status
            site_status = await self.mara_client.get_site_status()
            prices = await self.mara_client.get_current_prices()
            context["mara_status"] = {
                "site_status": site_status,
                "current_prices": prices
            }
            context["system_health"] = "operational"
            
        except Exception as e:
            context["system_health"] = f"mara_connection_error: {str(e)}"
        
        try:
            # Get recent market analysis if available
            market_intel = await self.allocation_agent.analyze_market_conditions()
            context["market_conditions"] = market_intel
            
        except Exception as e:
            context["market_conditions"] = f"analysis_error: {str(e)}"
        
        return context
    
    def _build_conversation_context(self, user_message: str, system_context: Dict[str, Any], additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Build comprehensive context for AI response generation"""
        
        # Recent conversation history
        recent_history = ""
        if self.conversation_history:
            recent_history = "\n".join([
                f"User: {conv['user_message']}\nAssistant: {conv['ai_response']}"
                for conv in self.conversation_history[-2:]  # Last 2 conversations only
            ])
        
        # Extract key metrics only
        site_status = system_context.get('mara_status', {}).get('site_status', {})
        key_metrics = {
            'power_used': site_status.get('total_power_used', 0),
            'revenue': site_status.get('total_revenue', 0),
            'miners': {
                'hydro': site_status.get('hydro_miners', 0),
                'immersion': site_status.get('immersion_miners', 0),
                'air': site_status.get('air_miners', 0),
                'gpu': site_status.get('gpu_compute', 0),
                'asic': site_status.get('asic_compute', 0)
            }
        }
        
        context_prompt = f"""You are MARA's AI assistant. Be EXTREMELY concise - 1-2 sentences maximum.

CURRENT STATE: {json.dumps(key_metrics)}
RECENT CHAT: {recent_history}

CRITICAL: 
- Answer in 1-2 short sentences only
- Use specific numbers from the data
- No explanations unless directly asked
- Be direct and factual

User: {user_message}
"""
        return context_prompt
    
    async def _generate_response(self, context_prompt: str) -> str:
        """Generate AI response using the context"""
        messages = [
            SystemMessage(content="You are MARA's AI assistant. Be EXTREMELY concise - maximum 1-2 short sentences. Use specific numbers. No lengthy explanations."),
            HumanMessage(content=context_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def get_system_summary(self) -> Dict[str, Any]:
        """Get a comprehensive system summary for dashboard display"""
        system_context = await self._get_system_context()
        
        summary_prompt = f"""Based on the current system state, provide a concise summary:

SYSTEM DATA:
{json.dumps(system_context, indent=2)}

Please provide:
1. Overall system health status
2. Current resource allocation efficiency
3. Bitcoin market conditions impact
4. Any alerts or recommendations
5. Recent performance highlights

Format as JSON with clear categories."""
        
        messages = [
            SystemMessage(content="You are a system analyst. Provide a structured summary of the MARA resource allocation system."),
            HumanMessage(content=summary_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Try to parse as JSON, fallback to plain text
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return {"summary": json.loads(json_match.group()), "raw_response": response.content}
            else:
                return {"summary": {"status": "generated", "content": response.content}, "raw_response": response.content}
        except:
            return {"summary": {"status": "text", "content": response.content}, "raw_response": response.content}
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.conversation_history[-limit:] if self.conversation_history else []
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []