import { styled, Input as TamaguiInput } from 'tamagui';

export const Input = styled(TamaguiInput, {
  name: 'Input',
  backgroundColor: '$background',
  borderWidth: 1,
  borderColor: '$borderColor',
  borderRadius: '$3',
  paddingHorizontal: '$3',
  paddingVertical: '$2',
  fontSize: '$3',
  color: '$text',
  placeholderTextColor: '$textMuted',
  focusStyle: {
    borderColor: '$primary',
    outlineWidth: 0,
  },
  variants: {
    size: {
      sm: {
        paddingHorizontal: '$2',
        paddingVertical: '$1',
        fontSize: '$2',
      },
      md: {
        paddingHorizontal: '$3',
        paddingVertical: '$2',
        fontSize: '$3',
      },
      lg: {
        paddingHorizontal: '$4',
        paddingVertical: '$3',
        fontSize: '$4',
      },
    },
    error: {
      true: {
        borderColor: '$error',
      },
    },
  } as const,
  defaultVariants: {
    size: 'md',
  },
});

