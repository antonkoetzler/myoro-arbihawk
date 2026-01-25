import type { EmptyStateProps } from '../types';

/**
 * Empty state component for displaying when there's no data
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className='flex flex-col items-center justify-center h-full min-h-[200px] text-center'>
      <div className='mb-4 rounded-full bg-slate-800/50 p-4'>
        <Icon size={24} className='text-slate-500' />
      </div>
      <p className='font-medium text-slate-400'>{title}</p>
      {description && (
        <p className='mt-1 text-sm text-slate-500'>{description}</p>
      )}
    </div>
  );
}
