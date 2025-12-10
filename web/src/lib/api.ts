const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const API_BASE_URL =
  (typeof import.meta !== 'undefined' &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE_URL) ||
  DEFAULT_API_BASE_URL;

export interface MaraPrice {
  energy_price: number;
  hash_price: number;
  token_price: number;
  timestamp: string;
}

export interface SiteStatus {
  air_miners: number;
  asic_compute: number;
  gpu_compute: number;
  hydro_miners: number;
  immersion_miners: number;
  total_power_used: number;
  total_revenue: number;
  total_power_cost: number;
  power: {
    [key: string]: number;
  };
  revenue: {
    [key: string]: number;
  };
}

export interface AllocationRequest {
  target_revenue?: number;
  inference_priority: number;
  power_limit?: number;
}

export interface AllocationResponse {
  allocation: {
    [key: string]: number;
  };
  expected_revenue: number;
  expected_cost: number;
  efficiency_score: number;
  reasoning: string;
}

export interface BTCData {
  price: number;
  change_24h: number;
  change_percent: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  market_cap: number;
  timestamp: string;
}

export interface MarketIntelligence {
  analysis: string;
  current_prices: MaraPrice[];
  inventory: any;
  timestamp: string;
  btc_data?: BTCData;
}

export interface ChatMessage {
  message: string;
  context?: any;
}

export interface ChatResponse {
  response: string;
  timestamp: string;
  context_used?: any;
  error?: boolean;
}

export interface ChatHistoryItem {
  timestamp: string;
  user_message: string;
  ai_response: string;
  system_context: any;
}

export interface SystemSummary {
  summary: any;
  raw_response: string;
}

export interface AgentOutput {
  timestamp: string;
  output: string;
  status: string;
}

export interface AgentOutputs {
  SimpleAllocationAgent: AgentOutput;
  ChatbotAgent: AgentOutput;
  MaraClient: AgentOutput;
  BTCClient: AgentOutput;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private buildUrl(endpoint: string): string {
    if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
      return endpoint;
    }

    const normalizedBase = this.baseUrl.replace(/\/+$/, '');
    const normalizedEndpoint = endpoint.replace(/^\/+/, '');
    return `${normalizedBase}/${normalizedEndpoint}`;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = this.buildUrl(endpoint);
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Fetch live status from backend
  async getStatus(): Promise<{ site_status: SiteStatus; current_prices: MaraPrice[]; btc_data: BTCData }> {
    return this.request<{ site_status: SiteStatus; current_prices: MaraPrice[]; btc_data: BTCData }>('/status');
  }

  // Optimize allocation through backend agent
  async optimizeAllocation(request: AllocationRequest): Promise<AllocationResponse> {
    return this.request<AllocationResponse>('/allocate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Deploy allocation via backend
  async deployAllocation(allocation: { [key: string]: number }): Promise<any> {
    return this.request<{ status: string; allocation: { [key: string]: number }; result?: any }>('/deploy', {
      method: 'POST',
      body: JSON.stringify(allocation),
    });
  }

  // Retrieve market intelligence summary
  async getMarketIntelligence(): Promise<MarketIntelligence> {
    return this.request<MarketIntelligence>('/market-intelligence');
  }

  // Load live BTC metrics
  async getBTCData(): Promise<BTCData> {
    return this.request<BTCData>('/btc');
  }

  // Chat with AI assistant
  async sendChatMessage(message: string, context?: any): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    });
  }

  async getSystemSummary(): Promise<SystemSummary> {
    return this.request<SystemSummary>('/chat/summary');
  }

  async getChatHistory(limit: number = 10): Promise<{ history: ChatHistoryItem[] }> {
    return this.request<{ history: ChatHistoryItem[] }>(`/chat/history?limit=${limit}`);
  }

  async clearChatHistory(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/chat/history', {
      method: 'DELETE',
    });
  }

  // Fetch latest agent outputs
  async getAgentOutputs(): Promise<AgentOutputs> {
    return this.request<AgentOutputs>('/agents/outputs');
  }
}

export const apiClient = new ApiClient();