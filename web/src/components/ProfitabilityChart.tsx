import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { apiClient, MaraPrice } from '../lib/api';
import { useState, useEffect, useCallback } from 'react';

const ProfitabilityChart = () => {
  const [priceHistory, setPriceHistory] = useState<MaraPrice[]>([]);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);

  const { data: statusData, isLoading } = useQuery({
    queryKey: ['status'],
    queryFn: () => apiClient.getStatus(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Use backend API for MARA price fetching (avoiding CORS issues)
  const fetchMaraPrices = useCallback(async () => {
    try {
      console.log('🔄 Fetching MARA prices from backend API...');
      const response = await apiClient.getStatus();
      if (response.current_prices) {
        const newPrices: MaraPrice[] = response.current_prices;
        console.log('📊 MARA API Prices fetched via backend:', {
          timestamp: new Date().toISOString(),
          pricesCount: newPrices.length,
          latestPrice: newPrices[0],
          priceRange: {
            hash: { min: Math.min(...newPrices.map(p => p.hash_price)), max: Math.max(...newPrices.map(p => p.hash_price)) },
            token: { min: Math.min(...newPrices.map(p => p.token_price)), max: Math.max(...newPrices.map(p => p.token_price)) },
            energy: { min: Math.min(...newPrices.map(p => p.energy_price)), max: Math.max(...newPrices.map(p => p.energy_price)) }
          }
        });
        
        // Store in localStorage for persistence
        localStorage.setItem('mara-price-history', JSON.stringify(newPrices));
        setPriceHistory(newPrices);
        setLastFetch(new Date());
      } else {
        console.error('❌ No price data in backend response');
      }
    } catch (error) {
      console.error('❌ Failed to fetch MARA prices from backend:', error);
    }
  }, []);

  // Load price history from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('mara-price-history');
    if (stored) {
      try {
        const parsedData = JSON.parse(stored);
        setPriceHistory(parsedData);
        console.log('📦 Loaded price history from storage:', parsedData.length, 'entries');
      } catch (error) {
        console.error('❌ Failed to parse stored price data:', error);
      }
    }
    
    // Initial fetch
    fetchMaraPrices();
  }, [fetchMaraPrices]);

  // Set up interval for continuous fetching (every 5 minutes to match API)
  useEffect(() => {
    const interval = setInterval(fetchMaraPrices, 5 * 60 * 1000); // 5 minutes
    return () => clearInterval(interval);
  }, [fetchMaraPrices]);

  // Combine and transform price data for the chart - use direct API data if available, fallback to status data
  const sourcePrices = priceHistory.length > 0 ? priceHistory : (statusData?.current_prices || []);
  
  // Debug logging to see actual price values and timestamps
  useEffect(() => {
    if (sourcePrices.length > 0) {
      const now = new Date();
      const currentPacificTime = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false,
        timeZone: 'America/Los_Angeles'
      });
      
      console.log('🔍 Current price data sample:', {
        source: priceHistory.length > 0 ? 'Direct API' : 'Backend',
        count: sourcePrices.length,
        currentSystemTime: now.toISOString(),
        currentPacificTime: currentPacificTime,
        latest: sourcePrices[0],
        latestTimestamp: sourcePrices[0]?.timestamp,
        latestPacificTime: new Date(sourcePrices[0]?.timestamp).toLocaleTimeString('en-US', {
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false,
          timeZone: 'America/Los_Angeles'
        }),
        first5Timestamps: sourcePrices.slice(0, 5).map(p => ({
          original: p.timestamp,
          pacific: new Date(p.timestamp).toLocaleTimeString('en-US', {
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false,
            timeZone: 'America/Los_Angeles'
          })
        }))
      });
    }
  }, [sourcePrices, priceHistory.length]);

  // Sort by timestamp to ensure chronological order (oldest to newest)
  const sortedPrices = [...sourcePrices].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const chartData = sortedPrices.slice(-50).map((price: MaraPrice, index: number) => {
    const timestamp = new Date(price.timestamp);
    const timeLabel = timestamp.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/Los_Angeles'
    });
    
    return {
      time: timeLabel,
      hash_price: Number(price.hash_price),
      token_price: Number(price.token_price),
      energy_price: Number(price.energy_price),
      // Calculate efficiency ratio
      efficiency: Number(price.token_price) / (Number(price.energy_price) || 1),
      timestamp: price.timestamp
    };
  }) || [];
  
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-terminal-surface p-3 border border-gray-600">
          <p className="text-terminal-muted font-mono text-sm">{`Time: ${label}`}</p>
          {payload.map((pld: any, index: number) => {
            const value = Number(pld.value);
            const formattedValue = pld.name === 'Efficiency' 
              ? value.toFixed(4) 
              : value.toLocaleString('en-US', { 
                  minimumFractionDigits: 2, 
                  maximumFractionDigits: 6 
                });
            
            return (
              <div key={index} className="flex items-center space-x-2 mt-1">
                <div className="w-2 h-2" style={{ backgroundColor: pld.stroke }}></div>
                <p className="text-white text-sm font-mono">
                  {`${pld.name}: ${pld.name === 'Efficiency' ? '' : '$'}${formattedValue}`}
                </p>
              </div>
            );
          })}
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <div className="bg-terminal-surface p-4 h-full flex items-center justify-center">
        <div className="text-terminal-muted">Loading market data...</div>
      </div>
    );
  }
  
  return (
    <div className="bg-terminal-surface p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-normal text-terminal-text">MARA Market Prices</h3>
        <div className="text-xs text-terminal-muted flex flex-col items-end">
          <div>
            {lastFetch && `Direct API: ${lastFetch.toLocaleTimeString()}`}
          </div>
          <div>
            {sourcePrices[0]?.timestamp && 
              `Latest data: ${new Date(sourcePrices[0].timestamp).toLocaleTimeString()}`
            }
          </div>
          <div className="text-terminal-accent">
            {chartData.length} data points • Auto-refresh: 5min
          </div>
        </div>
      </div>
      <div className="h-[calc(100%-80px)]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis 
              dataKey="time" 
              stroke="#6b7280" 
              fontSize={10}
            />
            <YAxis 
              stroke="#6b7280" 
              fontSize={10}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6b7280', strokeDasharray: '3 3' }} />
            <Legend wrapperStyle={{fontSize: "11px", color: "#6b7280"}}/>
            <Line name="Hash Price" type="monotone" dataKey="hash_price" stroke="#f59e0b" strokeWidth={2} activeDot={{ r: 4 }}/>
            <Line name="Token Price" type="monotone" dataKey="token_price" stroke="#3b82f6" strokeWidth={2} activeDot={{ r: 4 }}/>
            <Line name="Energy Price" type="monotone" dataKey="energy_price" stroke="#ef4444" strokeWidth={1.5} activeDot={{ r: 4 }}/>
            <Line name="Efficiency" type="monotone" dataKey="efficiency" stroke="#22c55e" strokeWidth={1.5} activeDot={{ r: 4 }}/>
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ProfitabilityChart;
