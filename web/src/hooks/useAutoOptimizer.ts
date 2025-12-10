import { useEffect, useRef, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

export const useAutoOptimizer = () => {
  const queryClient = useQueryClient();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const optimizeMutation = useMutation({
    mutationFn: () => apiClient.optimizeAllocation({
      inference_priority: 0.7, // Fixed at 70%
      // No target_revenue = maximize revenue
    }),
  });

  const deployMutation = useMutation({
    mutationFn: (allocation: { [key: string]: number }) => apiClient.deployAllocation(allocation),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status'] });
    },
  });

  const runOptimization = useCallback(async () => {
    try {
      console.log('🤖 Running auto-optimization...');
      const result = await optimizeMutation.mutateAsync();
      
      if (result && result.allocation) {
        console.log('📊 Deploying optimized allocation:', result.allocation);
        await deployMutation.mutateAsync(result.allocation);
        console.log('✅ Auto-optimization completed successfully');
      } else {
        console.warn('⚠️ No allocation returned from optimization');
      }
    } catch (error: any) {
      console.error('❌ Auto-optimization failed:', error);
      console.error('Error details:', error?.message || error);
    }
  }, [optimizeMutation, deployMutation]);

  useEffect(() => {
    // Run initial optimization after 5 seconds
    const initialTimeout = setTimeout(() => {
      runOptimization();
    }, 5000);

    // Then run every 30 seconds
    intervalRef.current = setInterval(() => {
      runOptimization();
    }, 30000);

    return () => {
      clearTimeout(initialTimeout);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [runOptimization]);

  return {
    isOptimizing: optimizeMutation.isPending,
    isDeploying: deployMutation.isPending,
    lastOptimization: optimizeMutation.data,
    error: optimizeMutation.error || deployMutation.error,
  };
};