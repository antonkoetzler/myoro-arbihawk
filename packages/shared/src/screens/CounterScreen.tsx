import { Button, Text, Heading, Card, VStack, HStack, Center } from '@repo/ui';
import { useTranslations } from '@repo/i18n';
import { useCounter } from '../hooks/useCounter';

interface CounterScreenProps {
  /** Whether to sync counter state with backend */
  syncWithBackend?: boolean;
}

export function CounterScreen({ syncWithBackend = false }: CounterScreenProps) {
  const t = useTranslations();
  const { value, increment, decrement, reset, isLoading, isMutating } = useCounter(syncWithBackend);

  if (isLoading) {
    return (
      <Center flex={1} padding="$4">
        <Text>{t.common.loading}</Text>
      </Center>
    );
  }

  return (
    <Center flex={1} padding="$4" backgroundColor="$background">
      <Card width="100%" maxWidth={400} padding="$6">
        <VStack gap="$6" alignItems="center">
          <Heading size="3xl">{t.counter.title}</Heading>
          
          <VStack gap="$2" alignItems="center">
            <Text variant="caption" size="sm">
              {t.counter.value}
            </Text>
            <Text size="4xl" fontWeight="700">
              {value}
            </Text>
          </VStack>

          <HStack gap="$3" flexWrap="wrap" justifyContent="center">
            <Button
              variant="primary"
              onPress={decrement}
              disabled={isMutating}
            >
              {t.counter.decrement}
            </Button>
            
            <Button
              variant="outline"
              onPress={reset}
              disabled={isMutating}
            >
              {t.counter.reset}
            </Button>
            
            <Button
              variant="primary"
              onPress={increment}
              disabled={isMutating}
            >
              {t.counter.increment}
            </Button>
          </HStack>
        </VStack>
      </Card>
    </Center>
  );
}

