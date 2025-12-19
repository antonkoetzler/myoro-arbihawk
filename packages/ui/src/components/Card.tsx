import { styled, YStack } from 'tamagui';

export const Card = styled(YStack, {
  name: 'Card',
  backgroundColor: '$surface',
  borderRadius: '$4',
  padding: '$4',
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.1,
  shadowRadius: 8,
  elevation: 2,
  variants: {
    variant: {
      elevated: {
        shadowOpacity: 0.15,
        shadowRadius: 12,
        elevation: 4,
      },
      outlined: {
        shadowOpacity: 0,
        elevation: 0,
        borderWidth: 1,
        borderColor: '$borderColor',
      },
      flat: {
        shadowOpacity: 0,
        elevation: 0,
      },
    },
  } as const,
  defaultVariants: {
    variant: 'elevated',
  },
});

