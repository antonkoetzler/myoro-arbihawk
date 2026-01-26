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

type Domain = 'betting' | 'trading';

/**
 * Models tab component - displays trained model versions and their performance
 * Shows both betting and trading models with domain separation
 */
export function ModelsTab({ api }: ModelsTabProps) {
  const [selectedDomain, setSelectedDomain] = useState<Domain>('betting');
  const [expandedMarket, setExpandedMarket] = useState<string | null>(null);

  const { data: bettingModels } = useQuery<ModelsResponse>({
    queryKey: ['models'],
    queryFn: api.getModels,
    refetchInterval: 30000,
    retry: false,
  });

  const { data: tradingModels } = useQuery({
    queryKey: ['trading-models'],
    queryFn: () => api.getTradingModels(),
    refetchInterval: 60000,
    retry: false,
  });

  const groupedBettingModels = useMemo(() => {
    if (!bettingModels?.versions) return {};

    const grouped: Record<string, ModelVersion[]> = {};
    bettingModels.versions.forEach((model) => {
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
  }, [bettingModels]);

  const tradingModelsList = useMemo(() => {
    if (!tradingModels || 'error' in tradingModels) return [];
    
    return Object.entries(tradingModels)
      .filter(([strategy]) => strategy !== 'error')
      .map(([strategy, model]: [string, any]) => ({
        strategy,
        available: model.available,
        cv_score: model.cv_score,
        version: model.version,
        created_at: model.created_at,
      }));
  }, [tradingModels]);

  const toggleMarket = (market: string) => {
    setExpandedMarket((prev) => (prev === market ? null : market));
  };

  const bettingMarkets = Object.keys(groupedBettingModels).sort();

  return (
    <div className='space-y-6'>
      <div className='card'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-semibold'>Model Versions</h3>
          <div className='flex items-center gap-3'>
            {/* Domain Selector */}
            <div className='flex items-center gap-1 rounded-lg bg-slate-800/50 p-1'>
              <button
                onClick={() => setSelectedDomain('betting')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  selectedDomain === 'betting'
                    ? 'bg-sky-500/20 text-sky-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
                type='button'
              >
                Betting
              </button>
              <button
                onClick={() => setSelectedDomain('trading')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  selectedDomain === 'trading'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
                type='button'
              >
                Trading
              </button>
            </div>
            <Tooltip text='Cross-Validation (CV) Score: Measures model accuracy using k-fold cross-validation. Higher scores (closer to 1.0) indicate better predictive performance. Each model is evaluated on multiple data folds to ensure reliability.'>
              <div className='flex items-center gap-1 cursor-help text-slate-400 hover:text-slate-300'>
                <span className='text-sm'>What's CV?</span>
                <HelpCircle size={16} className='text-slate-500' />
              </div>
            </Tooltip>
          </div>
        </div>
        <div className='space-y-2'>
          {selectedDomain === 'betting' ? (
            bettingMarkets.length > 0 ? (
              bettingMarkets.map((market) => {
                const marketModels = groupedBettingModels[market]!;
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
                          {model.brier_score !== undefined && (
                            <div className='mt-3 space-y-1 border-t border-slate-600 pt-3'>
                              <div className='flex items-center justify-between text-xs'>
                                <span className='text-slate-400'>Calibration Metrics:</span>
                                <Tooltip text='Brier Score: Measures probability accuracy (lower is better, perfect = 0.0). ECE (Expected Calibration Error): Measures how well predicted probabilities match actual frequencies (lower is better). Calibration ensures probabilities are reliable for betting decisions.'>
                                  <HelpCircle
                                    size={12}
                                    className='cursor-help text-slate-500'
                                  />
                                </Tooltip>
                              </div>
                              <div className='grid grid-cols-2 gap-2 text-xs'>
                                <div>
                                  <span className='text-slate-400'>Brier Score:</span>
                                  <span className='ml-2 font-mono text-slate-300'>
                                    {model.brier_score.toFixed(4)}
                                  </span>
                                </div>
                                <div>
                                  <span className='text-slate-400'>ECE:</span>
                                  <span className='ml-2 font-mono text-slate-300'>
                                    {model.ece?.toFixed(4) ?? '-'}
                                  </span>
                                </div>
                                {model.calibration_improvement && (
                                  <div className='col-span-2 text-xs text-slate-500'>
                                    Improvement: Brier{' '}
                                    {model.calibration_improvement.brier_score &&
                                      model.calibration_improvement.brier_score > 0 && (
                                        <span className='text-emerald-400'>+</span>
                                      )}
                                    {model.calibration_improvement.brier_score ? String(model.calibration_improvement.brier_score.toFixed(4)) : '0.0000'}, ECE{' '}
                                    {model.calibration_improvement.ece &&
                                      model.calibration_improvement.ece > 0 && (
                                        <span className='text-emerald-400'>+</span>
                                      )}
                                    {String(model.calibration_improvement.ece?.toFixed(4) ?? '0.0000')}
                                  </div>
                                )}
                                {(() => {
                                  const hyperparams = model.performance_metrics?.hyperparameters;
                                  if (hyperparams && typeof hyperparams === 'object' && hyperparams !== null) {
                                    return (
                                      <div className='col-span-2 mt-2 border-t border-slate-700/50 pt-2'>
                                        <div className='text-xs font-medium text-slate-400 mb-1'>
                                          Hyperparameters (Tuned):
                                        </div>
                                        <div className='text-xs text-slate-500 space-y-0.5'>
                                          {Object.entries(
                                            hyperparams as Record<string, unknown>
                                          ).map(([key, value]) => (
                                            <div key={key} className='flex justify-between'>
                                              <span className='text-slate-500'>{key}:</span>
                                              <span className='font-mono text-slate-400'>
                                                {typeof value === 'number' ? value.toFixed(4) : String(value)}
                                              </span>
                                            </div>
                                          ))}
                                        </div>
                                        {(() => {
                                          const tuningMetrics = model.performance_metrics?.tuning_metrics;
                                          if (tuningMetrics && typeof tuningMetrics === 'object' && tuningMetrics !== null && 'best_brier_score' in tuningMetrics) {
                                            const score = (tuningMetrics as Record<string, unknown>).best_brier_score as number ?? 0;
                                            return (
                                              <div className='mt-1 text-xs text-slate-500'>
                                                Tuning Brier: {score.toFixed(4)}
                                              </div>
                                            );
                                          }
                                          return null;
                                        })()}
                                      </div>
                                    );
                                  }
                                  return null;
                                })()}
                              </div>
                            </div>
                          )}
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
                title='No Betting Models Yet'
                description='Train betting models to see them here'
              />
            )
          ) : (
            tradingModelsList.length > 0 ? (
              tradingModelsList.map((model) => {
                const isExpanded = expandedMarket === model.strategy;
                return (
                  <div key={model.strategy} className='rounded-lg border border-slate-700 bg-slate-700/30'>
                    <button
                      onClick={() => toggleMarket(model.strategy)}
                      className='w-full p-4 text-left hover:bg-slate-700/50 transition-colors'
                    >
                      <div className='flex items-center justify-between'>
                        <div className='flex items-center gap-2'>
                          {isExpanded ? (
                            <ChevronDown size={18} className='text-slate-400' />
                          ) : (
                            <ChevronRight size={18} className='text-slate-400' />
                          )}
                          <p className='font-medium capitalize'>{model.strategy}</p>
                          {model.available && (
                            <span className='rounded bg-emerald-500 px-2 py-0.5 text-xs text-white'>
                              Active
                            </span>
                          )}
                        </div>
                        <div className='text-right'>
                          {model.available && model.cv_score !== undefined && (
                            <>
                              <p className='font-mono'>{model.cv_score.toFixed(4)}</p>
                              <p className='text-xs text-slate-400'>CV Score</p>
                            </>
                          )}
                        </div>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className='border-t border-slate-700 bg-slate-800/30'>
                        <div className='ml-8 mr-4 mb-4 mt-4 rounded-lg border border-slate-600 bg-slate-700/20 p-4'>
                          <div className='space-y-2'>
                            <div className='flex items-center justify-between'>
                              <span className='text-sm text-slate-400'>Status:</span>
                              <span className={`px-2 py-1 rounded text-xs ${
                                model.available 
                                  ? 'bg-emerald-500/20 text-emerald-400' 
                                  : 'bg-slate-700/50 text-slate-400'
                              }`}>
                                {model.available ? 'Trained' : 'Not Trained'}
                              </span>
                            </div>
                            {model.available && (
                              <>
                                {model.cv_score !== undefined && (
                                  <div className='flex items-center justify-between'>
                                    <span className='text-sm text-slate-400'>CV Score:</span>
                                    <span className='font-mono text-slate-300'>
                                      {(model.cv_score * 100).toFixed(2)}%
                                    </span>
                                  </div>
                                )}
                                {model.version && (
                                  <div className='flex items-center justify-between'>
                                    <span className='text-sm text-slate-400'>Version:</span>
                                    <span className='font-mono text-slate-300'>{model.version}</span>
                                  </div>
                                )}
                                {model.created_at && (
                                  <div className='flex items-center justify-between'>
                                    <span className='text-sm text-slate-400'>Created:</span>
                                    <span className='text-sm text-slate-300'>
                                      {new Date(model.created_at).toLocaleString()}
                                    </span>
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <EmptyState
                icon={RefreshCw}
                title='No Trading Models Yet'
                description='Train trading models to see them here'
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}
