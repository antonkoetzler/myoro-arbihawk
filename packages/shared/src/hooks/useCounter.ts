import { useCounterStore } from '../stores/counter';
import { trpc } from '../services/api';
import { useCallback } from 'react';

/**
 * Hook for counter operations with optional backend sync
 * @param sync - Whether to sync with backend (requires tRPC provider)
 */
export function useCounter(sync: boolean = false) {
  const store = useCounterStore();
  
  // Backend queries (only used when sync is true)
  const counterQuery = trpc.counter.get.useQuery(undefined, {
    enabled: sync,
    onSuccess: (data) => {
      store.setValue(data.value);
    },
  });
  
  const incrementMutation = trpc.counter.increment.useMutation({
    onSuccess: (data) => {
      store.setValue(data.value);
    },
  });
  
  const decrementMutation = trpc.counter.decrement.useMutation({
    onSuccess: (data) => {
      store.setValue(data.value);
    },
  });
  
  const resetMutation = trpc.counter.reset.useMutation({
    onSuccess: (data) => {
      store.setValue(data.value);
    },
  });

  const increment = useCallback(() => {
    if (sync) {
      incrementMutation.mutate();
    } else {
      store.increment();
    }
  }, [sync, store, incrementMutation]);

  const decrement = useCallback(() => {
    if (sync) {
      decrementMutation.mutate();
    } else {
      store.decrement();
    }
  }, [sync, store, decrementMutation]);

  const reset = useCallback(() => {
    if (sync) {
      resetMutation.mutate();
    } else {
      store.reset();
    }
  }, [sync, store, resetMutation]);

  return {
    value: store.value,
    increment,
    decrement,
    reset,
    isLoading: sync && counterQuery.isLoading,
    isMutating: incrementMutation.isLoading || decrementMutation.isLoading || resetMutation.isLoading,
  };
}

