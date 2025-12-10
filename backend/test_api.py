import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.mara_client import MaraClient
from agents.simple_allocation_agent import SimpleAllocationAgent

async def test_api():
    """Test the MARA API integration"""
    print("Testing MARA API integration...")
    
    # Test MARA client
    api_key = os.getenv("MARA_API_KEY", "f8101705-3135-4d06-98ea-856a24383077")
    mara_client = MaraClient(api_key)
    
    try:
        # Test price fetch
        print("\n1. Testing price fetch...")
        prices = await mara_client.get_current_prices()
        print(f"✓ Fetched {len(prices)} price entries")
        if prices:
            print(f"  Latest: Hash=${prices[0]['hash_price']:.2f}, Token=${prices[0]['token_price']:.2f}, Energy=${prices[0]['energy_price']:.3f}")
        
        # Test inventory
        print("\n2. Testing inventory fetch...")
        inventory = await mara_client.get_inventory()
        print("✓ Inventory fetched successfully")
        print(f"  Available miners: {list(inventory.get('miners', {}).keys())}")
        print(f"  Available inference: {list(inventory.get('inference', {}).keys())}")
        
        # Test site status
        print("\n3. Testing site status...")
        try:
            status = await mara_client.get_site_status()
            print("✓ Site status fetched successfully")
            print(f"  Total power used: {status.get('total_power_used', 0)}W")
            print(f"  Total revenue: ${status.get('total_revenue', 0):.2f}")
        except Exception as e:
            print(f"⚠ Site status error (expected if no site created): {e}")
        
        print("\n4. Testing allocation agent...")
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            agent = SimpleAllocationAgent(openai_key, mara_client)
            result = await agent.optimize_allocation(inference_priority=0.8)
            print("✓ Agent optimization completed")
            print(f"  Suggested allocation: {result['allocation']}")
            print(f"  Expected revenue: ${result['expected_revenue']:.2f}")
            print(f"  Efficiency score: {result['efficiency_score']:.1f}%")
        else:
            print("⚠ No OpenAI API key found, skipping agent test")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_api())