import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, HelpCircle, ChevronRight, ChevronDown } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import { Tooltip } from '../Tooltip';
import { marketDescriptions } from '../../utils/constants';
import type { createApi } from '../../api/api';
import type { ModelsResponse, ModelVersion } from '../../types';

interface ModelsTabProps {
  api: ReturnType<typeof createApi>;
}

/**
 * Models tab component - displays trained model versions and their performance
 */
export function ModelsTab({ api }: ModelsTabProps) {
  const { data: models } = useQuery<ModelsResponse>({
    queryKey: ['models'],
    queryFn: api.getModels,
    refetchInterval: 30000,
    retry: false,
  });

  const [expandedMarket, setExpandedMarket] = useState<string | null>(null);

  const groupedModels = useMemo(() => {
    if (!models?.versions) return {};

    const grouped: Record<string, ModelVersion[]> = {};
    models.versions.forEach((model) => {
      if (!grouped[model.market]) {
        grouped[model.market] = [];
      }
      grouped[model.market]!.push(model);
    });

    // Sort versions within each group by version_id (descending - newest first)
    Object.keys(grouped).forEach((market) => {
      grouped[market]!.sort((a, b) => b.version_id - a.version_id);
    });

    return grouped;
  }, [models]);

  const toggleMarket = (market: string) => {
    setExpandedMarket((prev) => (prev === market ? null : market));
  };

  const markets = Object.keys(groupedModels).sort();

  return (
    <div className='space-y-6'>
      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Model Versions</h3>
          <Tooltip text='Cross-Validation (CV) Score: Measures model accuracy using k-fold cross-validation. Higher scores (closer to 1.0) indicate better predictive performance. Each model is evaluated on multiple data folds to ensure reliability.'>
            <div className='flex items-center gap-1 cursor-help text-slate-400 hover:text-slate-300'>
              <span className='text-sm'>What's CV?</span>
              <HelpCircle size={16} className='text-slate-500' />
            </div>
          </Tooltip>
        </div>
        <div className='space-y-2'>
          {markets.length > 0 ? (
            markets.map((market) => {
              const marketModels = groupedModels[market]!;
              const isExpanded = expandedMarket === market;
              const description =
                marketDescriptions[market] ?? 'Betting market prediction model';
              const activeModel = marketModels.find((m) => m.is_active);

              return (
                <div key={market} className='rounded-lg border border-slate-700 bg-slate-700/30'>
                  <button
                    onClick={() => toggleMarket(market)}
                    className='w-full p-4 text-left hover:bg-slate-700/50 transition-colors'
                  >
                    <div className='flex items-center justify-between'>
                      <div className='flex items-center gap-2'>
                        {isExpanded ? (
                          <ChevronDown size={18} className='text-slate-400' />
                        ) : (
                          <ChevronRight size={18} className='text-slate-400' />
                        )}
                        <p className='font-medium'>{market}</p>
                        {activeModel && (
                          <span className='rounded bg-sky-500 px-2 py-0.5 text-xs text-white'>
                            Active: v{activeModel.version_id}
                          </span>
                        )}
                        <span className='text-xs text-slate-500'>
                          ({marketModels.length} version{marketModels.length !== 1 ? 's' : ''})
                        </span>
                      </div>
                      <Tooltip text={description}>
                        <HelpCircle
                          size={14}
                          className='cursor-help text-slate-500'
                        />
                      </Tooltip>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className='border-t border-slate-700 bg-slate-800/30'>
                      {marketModels.map((model) => (
                        <div
                          key={model.version_id}
                          className={`ml-8 mr-4 mb-4 mt-4 rounded-lg border p-4 ${model.is_active
                            ? 'border-sky-500/50 bg-sky-500/10'
                            : 'border-slate-600 bg-slate-700/20'
                            }`}
                        >
                          <div className='flex items-start justify-between'>
                            <div>
                              <div className='flex items-center gap-2'>
                                <p className='font-medium'>
                                  Version {model.version_id}
                                </p>
                                {model.is_active && (
                                  <span className='rounded bg-sky-500 px-2 py-0.5 text-xs text-white'>
                                    Active
                                  </span>
                                )}
                              </div>
                              <p className='mt-1 text-xs text-slate-500'>
                                {description}
                              </p>
                            </div>
                            <div className='text-right'>
                              <p className='font-mono'>
                                {model.cv_score?.toFixed(4) ?? '-'}
                              </p>
                              <p className='text-xs text-slate-400'>CV Score</p>
                            </div>
                          </div>
                          <div className='mt-3 flex gap-4 text-sm text-slate-400'>
                            <span>Samples: {model.training_samples}</span>
                            <span>
                              Trained: {model.trained_at?.split('T')[0]}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <EmptyState
              icon={RefreshCw}
              title='No Models Yet'
              description='Train models to see them here'
            />
          )}
        </div>
      </div>
    </div>
  );
}
