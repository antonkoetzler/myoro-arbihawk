import { styled, XStack as TamaguiXStack, YStack as TamaguiYStack } from 'tamagui';

export const VStack = styled(TamaguiYStack, {
  name: 'VStack',
});

export const HStack = styled(TamaguiXStack, {
  name: 'HStack',
});

export const Center = styled(TamaguiYStack, {
  name: 'Center',
  alignItems: 'center',
  justifyContent: 'center',
});

