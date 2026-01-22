import type { StatCardProps } from '../types';

/**
 * Stat card component for displaying metrics
 */
export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
}: StatCardProps) {
  // Determine icon background based on trend - null means neutral (no data)
  const getTrendClasses = (): string => {
    if (trend === 'up') return 'bg-emerald-500/20 text-emerald-400';
    if (trend === 'down') return 'bg-red-500/20 text-red-400';
    // Neutral state (null or undefined)
    return 'bg-slate-700/50 text-slate-400';
  };

  return (
    <div className='stat-card'>
      <div className='flex items-start justify-between'>
        <div>
          <p className='mb-1 text-sm text-slate-400'>{title}</p>
          <p className='text-2xl font-bold'>{value}</p>
          {subtitle && (
            <p className='mt-1 text-xs text-slate-500'>{subtitle}</p>
          )}
        </div>
        <div className={`rounded-lg p-4 ${getTrendClasses()}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}
