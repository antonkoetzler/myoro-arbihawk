import { styled, Text as TamaguiText } from 'tamagui';

export const Text = styled(TamaguiText, {
  name: 'Text',
  color: '$text',
  fontFamily: '$body',
  variants: {
    variant: {
      heading: {
        fontFamily: '$heading',
        fontWeight: '700',
      },
      subheading: {
        fontFamily: '$heading',
        fontWeight: '600',
      },
      body: {
        fontFamily: '$body',
        fontWeight: '400',
      },
      caption: {
        fontFamily: '$body',
        fontWeight: '400',
        color: '$textMuted',
      },
    },
    size: {
      xs: { fontSize: '$1' },
      sm: { fontSize: '$2' },
      md: { fontSize: '$3' },
      lg: { fontSize: '$4' },
      xl: { fontSize: '$5' },
      '2xl': { fontSize: '$6' },
      '3xl': { fontSize: '$7' },
      '4xl': { fontSize: '$8' },
    },
  } as const,
  defaultVariants: {
    variant: 'body',
    size: 'md',
  },
});

export const Heading = styled(Text, {
  name: 'Heading',
  variant: 'heading',
  size: '2xl',
});

