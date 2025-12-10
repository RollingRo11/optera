import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useQuery } from '@tanstack/react-query';

const AiMarketIndicators = () => {
  const { data: cryptoPrices } = useQuery({
    queryKey: ['crypto-ai-tokens'],
    queryFn: async () => {
      try {
        const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=render-token,akash-network,golem&vs_currencies=usd');
        return response.json();
      } catch (error) {
        console.warn('CoinGecko API unavailable');
        return null;
      }
    },
    refetchInterval: 300000,
    retry: false,
  });

  const apiPricing = [
    { provider: 'OpenAI (GPT-4o)', price: '$0.0025/1k tok', change: '+2.1%' },
    { provider: 'OpenAI (GPT-4o)', price: '$0.003/1k tok', change: '0%' },
    { provider: 'Local Model', price: '$0.002/1k tok (est.)', change: '-5.2%' }
  ];

  const gpuPricing = [
    { provider: 'Lambda (H100)', price: '$1.85/hr', availability: 'High' },
    { provider: 'RunPod (H100)', price: '$2.99/hr', availability: 'Medium' },
    { provider: 'AWS (H100)', price: '$8.84/hr', availability: 'High' },
    { provider: 'DataCrunch (H100)', price: '$3.35/hr', availability: 'Low' },
    { provider: 'Azure (H100)', price: '$6.98/hr', availability: 'Medium' },
    { provider: 'GCP (H100)', price: '$11.04/hr', availability: 'High' }
  ];

  const aiTokens = [
    { 
      token: 'RENDER', 
      price: cryptoPrices?.['render-token']?.usd ? `$${cryptoPrices['render-token'].usd.toFixed(3)}` : '$7.35',
      change: '+15.2%'
    },
    { 
      token: 'AKT', 
      price: cryptoPrices?.['akash-network']?.usd ? `$${cryptoPrices['akash-network'].usd.toFixed(3)}` : '$3.78',
      change: '+8.4%'
    },
    { 
      token: 'GLM', 
      price: cryptoPrices?.['golem']?.usd ? `$${cryptoPrices['golem'].usd.toFixed(3)}` : '$0.32',
      change: '-2.1%'
    }
  ];

  return (
    <Card className="bg-terminal-surface border-terminal-border">
      <CardHeader>
        <CardTitle className="text-terminal-accent">AI Market Indicators</CardTitle>
      </CardHeader>
      <CardContent>
        <h4 className="font-semibold text-white mb-2">GPU Cloud Pricing (H100)</h4>
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead className="text-terminal-muted">Provider</TableHead>
                    <TableHead className="text-right text-terminal-muted">Price/hr</TableHead>
                    <TableHead className="text-right text-terminal-muted">Availability</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {gpuPricing.slice(0, 4).map(item => (
                    <TableRow key={item.provider}>
                        <TableCell className="text-white font-mono text-xs">{item.provider}</TableCell>
                        <TableCell className="text-right text-white font-mono text-xs">{item.price}</TableCell>
                        <TableCell className={`text-right font-mono text-xs ${
                          item.availability === 'High' ? 'text-terminal-success' : 
                          item.availability === 'Medium' ? 'text-terminal-warning' : 'text-terminal-error'
                        }`}>
                          {item.availability}
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>

        <h4 className="font-semibold text-white mt-4 mb-2">AI/Compute Tokens</h4>
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead className="text-terminal-muted">Token</TableHead>
                    <TableHead className="text-right text-terminal-muted">Price</TableHead>
                    <TableHead className="text-right text-terminal-muted">24h Change</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {aiTokens.map(item => (
                    <TableRow key={item.token}>
                        <TableCell className="text-white font-mono text-xs">{item.token}</TableCell>
                        <TableCell className="text-right text-white font-mono text-xs">{item.price}</TableCell>
                        <TableCell className={`text-right font-mono text-xs ${
                          item.change.startsWith('+') ? 'text-terminal-success' : 'text-terminal-error'
                        }`}>
                          {item.change}
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default AiMarketIndicators; 