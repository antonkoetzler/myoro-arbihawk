import { styled, Button as TamaguiButton } from 'tamagui';

export const Button = styled(TamaguiButton, {
  name: 'Button',
  backgroundColor: '$primary',
  color: 'white',
  borderRadius: '$4',
  paddingHorizontal: '$4',
  paddingVertical: '$3',
  fontWeight: '600',
  pressStyle: {
    backgroundColor: '$primaryActive',
    scale: 0.98,
  },
  hoverStyle: {
    backgroundColor: '$primaryHover',
  },
  variants: {
    variant: {
      primary: {
        backgroundColor: '$primary',
      },
      secondary: {
        backgroundColor: '$secondary',
      },
      outline: {
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderColor: '$primary',
        color: '$primary',
      },
      ghost: {
        backgroundColor: 'transparent',
        color: '$primary',
      },
    },
    size: {
      sm: {
        paddingHorizontal: '$3',
        paddingVertical: '$2',
        fontSize: '$2',
      },
      md: {
        paddingHorizontal: '$4',
        paddingVertical: '$3',
        fontSize: '$3',
      },
      lg: {
        paddingHorizontal: '$5',
        paddingVertical: '$4',
        fontSize: '$4',
      },
    },
  } as const,
  defaultVariants: {
    variant: 'primary',
    size: 'md',
  },
});

