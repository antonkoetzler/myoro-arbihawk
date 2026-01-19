import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, TrendingUp, Clock, Database, Play, Square, RefreshCw, Download, AlertCircle, Inbox, Info, HelpCircle } from 'lucide-react'

// API functions
const api = {
  getHealth: () => fetch('/api/health').then(r => r.json()),
  getMetricsSummary: () => fetch('/api/metrics/summary').then(r => r.json()),
  getBankroll: () => fetch('/api/bankroll').then(r => r.json()),
  getBets: (limit = 50) => fetch(`/api/bets?limit=${limit}`).then(r => r.json()),
  getModels: () => fetch('/api/models').then(r => r.json()),
  getAutomationStatus: () => fetch('/api/automation/status').then(r => r.json()),
  getErrors: () => fetch('/api/errors').then(r => r.json()),
  getDbStats: () => fetch('/api/database/stats').then(r => r.json()),
  triggerAutomation: (mode) => fetch('/api/automation/trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  }).then(r => r.json()),
  stopAutomation: () => fetch('/api/automation/stop', { method: 'POST' }).then(r => r.json()),
}

// Messages that indicate a new task is starting (should clear logs)
const TASK_START_PATTERNS = [
  'Starting model training',
  'Starting data collection',
  'Starting full automation cycle'
]

// WebSocket hook for real-time logs
function useWebSocketLogs() {
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  // Function to clear logs (exposed for external use)
  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  const connect = useCallback(() => {
    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`
    
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // Ignore ping messages
          if (data.type === 'ping') return
          
          // Check if this message indicates a new task starting
          const isTaskStart = TASK_START_PATTERNS.some(
            pattern => data.message?.includes(pattern)
          )
          
          setLogs(prev => {
            // If a new task is starting, clear previous logs and start fresh
            if (isTaskStart) {
              return [data]
            }
            
            // Prevent duplicates by checking timestamp + message
            const isDuplicate = prev.some(
              log => log.timestamp === data.timestamp && log.message === data.message
            )
            if (isDuplicate) return prev
            
            // Keep only last 500 logs
            const newLogs = [...prev, data]
            return newLogs.slice(-500)
          })
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        console.log('WebSocket disconnected, reconnecting...')
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        ws.close()
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      reconnectTimeoutRef.current = setTimeout(connect, 3000)
    }
  }, [])

  useEffect(() => {
    connect()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connect])

  return { logs, connected, clearLogs }
}

// Tooltip component - only shows when text is provided
function Tooltip({ text, children, className = '', position = 'auto' }) {
  const [show, setShow] = useState(false)
  const [tooltipStyle, setTooltipStyle] = useState({})
  const tooltipRef = useRef(null)
  const containerRef = useRef(null)
  
  // Don't add tooltip behavior if there's no text
  if (!text) {
    return <div className={className}>{children}</div>
  }
  
  const updatePosition = () => {
    if (!tooltipRef.current || !containerRef.current) return
    
    const tooltip = tooltipRef.current
    const container = containerRef.current
    const tooltipRect = tooltip.getBoundingClientRect()
    const containerRect = container.getBoundingClientRect()
    
    const viewportWidth = window.innerWidth
    const margin = 8
    
    let style = { placement: 'top', xAlign: 'center' }
    
    // Check if tooltip would overflow top - place below instead
    if (tooltipRect.top < margin) {
      style.placement = 'bottom'
    }
    
    // Check horizontal overflow
    const centerX = containerRect.left + containerRect.width / 2
    const tooltipHalfWidth = tooltipRect.width / 2
    
    if (centerX - tooltipHalfWidth < margin) {
      style.xAlign = 'left'
    } else if (centerX + tooltipHalfWidth > viewportWidth - margin) {
      style.xAlign = 'right'
    }
    
    setTooltipStyle(style)
  }
  
  const handleMouseEnter = () => {
    setShow(true)
    // Use requestAnimationFrame to ensure DOM is updated
    requestAnimationFrame(() => {
      requestAnimationFrame(updatePosition)
    })
  }
  
  return (
    <div ref={containerRef} className={`relative inline-flex items-center ${className}`}>
      <div
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setShow(false)}
        className="cursor-help"
      >
        {children}
      </div>
      {show && (
        <div 
          ref={tooltipRef}
          className={`absolute px-3 py-2 text-xs bg-slate-900 text-slate-200 rounded whitespace-normal min-w-[200px] max-w-xs z-50 border border-slate-700 shadow-lg ${
            tooltipStyle.placement === 'bottom' ? 'top-full mt-2' : 'bottom-full mb-2'
          } ${
            tooltipStyle.xAlign === 'left' ? 'left-0' : 
            tooltipStyle.xAlign === 'right' ? 'right-0' : 
            'left-1/2 -translate-x-1/2'
          }`}
        >
          {text}
          <div className={`absolute ${
            tooltipStyle.placement === 'bottom' 
              ? 'bottom-full left-1/2 -translate-x-1/2 border-4 border-transparent border-b-slate-900' 
              : 'top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900'
          }`} />
        </div>
      )}
    </div>
  )
}

// Empty state component
function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="p-3 rounded-full bg-slate-700/30 mb-3">
        <Icon size={24} className="text-slate-500" />
      </div>
      <p className="font-medium text-slate-400">{title}</p>
      {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
    </div>
  )
}

// Database stat tooltips
const dbStatTooltips = {
  fixtures: 'Total number of match fixtures stored in the database',
  odds: 'Total betting odds records across all fixtures',
  bets: 'Total bets placed through the system',
  models: 'Number of trained model versions',
  scores: 'Match scores collected from external sources',
  ingestions: 'Number of data ingestion operations performed',
}

function StatCard({ title, value, subtitle, icon: Icon, trend }) {
  // Determine icon background based on trend - null means neutral (no data)
  const getTrendClasses = () => {
    if (trend === 'up') return 'bg-emerald-500/20 text-emerald-400'
    if (trend === 'down') return 'bg-red-500/20 text-red-400'
    // Neutral state (null or undefined)
    return 'bg-slate-700/50 text-slate-400'
  }
  
  return (
    <div className="stat-card">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-slate-400 text-sm mb-1">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {subtitle && <p className="text-slate-500 text-xs mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${getTrendClasses()}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  )
}

// Get log level color class
function getLogLevelColor(level) {
  switch (level?.toLowerCase()) {
    case 'error':
      return 'text-red-400'
    case 'warning':
      return 'text-yellow-400'
    case 'info':
      return 'text-sky-400'
    case 'success':
    case 'ok':
      return 'text-emerald-400'
    default:
      return 'text-slate-300'
  }
}

// Define which queries are needed for each tab
const TAB_QUERIES = {
  overview: ['health', 'metrics', 'bankroll', 'bets', 'errors', 'dbStats', 'status'],
  betting: ['bets', 'bankroll'],
  automation: ['status'],
  models: ['models'],
  logs: [] // No polling needed - WebSocket handles it
}

function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const queryClient = useQueryClient()
  const logsContainerRef = useRef(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // WebSocket logs with clear function
  const { logs: wsLogs, connected: wsConnected, clearLogs } = useWebSocketLogs()

  // Helper to determine if a query should be enabled and polling
  const shouldPoll = (queryKey) => TAB_QUERIES[activeTab]?.includes(queryKey)

  // Queries with tab-based polling
  const { data: health } = useQuery({ 
    queryKey: ['health'], 
    queryFn: api.getHealth,
    refetchInterval: shouldPoll('health') ? 30000 : false
  })
  const { data: metrics } = useQuery({ 
    queryKey: ['metrics'], 
    queryFn: api.getMetricsSummary,
    refetchInterval: shouldPoll('metrics') ? 30000 : false
  })
  const { data: bankroll } = useQuery({ 
    queryKey: ['bankroll'], 
    queryFn: api.getBankroll,
    refetchInterval: shouldPoll('bankroll') ? 30000 : false
  })
  const { data: bets } = useQuery({ 
    queryKey: ['bets'], 
    queryFn: () => api.getBets(50),
    refetchInterval: shouldPoll('bets') ? 30000 : false
  })
  const { data: models } = useQuery({ 
    queryKey: ['models'], 
    queryFn: api.getModels,
    refetchInterval: shouldPoll('models') ? 30000 : false
  })
  const { data: status } = useQuery({ 
    queryKey: ['status'], 
    queryFn: api.getAutomationStatus,
    refetchInterval: shouldPoll('status') ? 30000 : false
  })
  const { data: errors } = useQuery({ 
    queryKey: ['errors'], 
    queryFn: api.getErrors,
    refetchInterval: shouldPoll('errors') ? 30000 : false
  })
  const { data: dbStats } = useQuery({ 
    queryKey: ['dbStats'], 
    queryFn: api.getDbStats,
    refetchInterval: shouldPoll('dbStats') ? 30000 : false
  })

  // Mutations
  const triggerMutation = useMutation({
    mutationFn: api.triggerAutomation,
    onSuccess: () => {
      queryClient.invalidateQueries(['status'])
      // Clear logs when a new task starts (backup - WebSocket should also handle this)
      clearLogs()
    }
  })

  const stopMutation = useMutation({
    mutationFn: api.stopAutomation,
    onSuccess: () => queryClient.invalidateQueries(['status'])
  })

  // Auto-scroll logs to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [wsLogs, autoScroll])

  // Scroll to bottom when logs tab is clicked
  useEffect(() => {
    if (activeTab === 'logs' && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
      setAutoScroll(true)
    }
  }, [activeTab])

  // Invalidate and refetch queries for the new tab when switching
  useEffect(() => {
    const queriesToRefetch = TAB_QUERIES[activeTab] || []
    queriesToRefetch.forEach(key => {
      queryClient.invalidateQueries([key])
    })
  }, [activeTab, queryClient])

  // Handle manual scroll to disable auto-scroll
  const handleLogsScroll = (e) => {
    const container = e.target
    const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50
    setAutoScroll(isAtBottom)
  }
  
  // Determine if buttons should be disabled and get tooltip text
  const isTaskRunning = !!status?.current_task
  const taskButtonTooltip = isTaskRunning ? 'You can only run one task at a time' : ''
  const stopButtonTooltip = !isTaskRunning ? 'No task is currently running' : ''

  const formatPercent = (val) => val ? `${(val * 100).toFixed(1)}%` : '0%'
  const formatMoney = (val) => val ? `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00'
  
  // Determine win rate trend - neutral when no wins AND no losses
  const getWinRateTrend = () => {
    const wins = bankroll?.wins || 0
    const losses = bankroll?.losses || 0
    if (wins === 0 && losses === 0) return null // Neutral
    return bankroll?.win_rate > 0.5 ? 'up' : 'down'
  }

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <header className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-400 to-cyan-400 bg-clip-text text-transparent">
              Arbihawk Dashboard
            </h1>
            <p className="text-slate-400 mt-1">Betting Prediction System</p>
          </div>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${health?.status === 'healthy' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
              <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`} />
              {health?.status === 'healthy' ? 'Healthy' : health?.status ? health.status.charAt(0).toUpperCase() + health.status.slice(1) : 'Unknown'}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="flex gap-2 mb-6 border-b border-slate-700/50 pb-4">
        {['overview', 'betting', 'automation', 'models', 'logs'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg capitalize transition-all ${activeTab === tab ? 'bg-sky-500 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'}`}
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Balance"
              value={formatMoney(bankroll?.current_balance)}
              subtitle={`Started: ${formatMoney(bankroll?.starting_balance)}`}
              icon={TrendingUp}
              trend={bankroll?.profit > 0 ? 'up' : bankroll?.profit < 0 ? 'down' : null}
            />
            <StatCard
              title="ROI"
              value={formatPercent(bankroll?.roi)}
              subtitle={`Profit: ${formatMoney(bankroll?.profit)}`}
              icon={Activity}
              trend={bankroll?.roi > 0 ? 'up' : bankroll?.roi < 0 ? 'down' : null}
            />
            <StatCard
              title="Win Rate"
              value={formatPercent(bankroll?.win_rate)}
              subtitle={`${bankroll?.wins || 0}W / ${bankroll?.losses || 0}L`}
              icon={TrendingUp}
              trend={getWinRateTrend()}
            />
            <StatCard
              title="Total Bets"
              value={bankroll?.total_bets || 0}
              subtitle={`Pending: ${bankroll?.pending_bets || 0}`}
              icon={Database}
            />
          </div>

          {/* Errors Card - Always visible */}
          <div className={`card ${errors?.total_errors > 0 ? 'border-red-500/50 bg-red-500/10' : ''}`}>
            <div className="flex items-center gap-3 mb-4">
              <AlertCircle className={errors?.total_errors > 0 ? 'text-red-400' : 'text-slate-500'} />
              <div>
                <p className={`font-medium ${errors?.total_errors > 0 ? 'text-red-400' : 'text-slate-400'}`}>
                  {errors?.total_errors > 0 ? 'Errors Detected' : 'No Errors'}
                </p>
                <p className="text-sm text-slate-400">
                  {errors?.total_errors > 0 
                    ? `${errors.total_errors} errors in the last 24 hours`
                    : 'System is running smoothly'
                  }
                </p>
              </div>
            </div>
            
            {/* Error Details Section */}
            {errors?.total_errors > 0 && (
              <div className="space-y-3 mt-4 pt-4 border-t border-slate-700/50">
                <p className="text-sm font-medium text-slate-300">Error Details</p>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {errors?.log_errors?.map((err, i) => (
                    <div key={`log-${i}`} className="bg-slate-800/50 rounded p-2 text-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">Log</span>
                        <span className="text-xs text-slate-500">{err.timestamp}</span>
                      </div>
                      <p className="text-red-400 text-xs font-mono break-all">{err.message}</p>
                    </div>
                  ))}
                  {errors?.ingestion_errors?.map((err, i) => (
                    <div key={`ing-${i}`} className="bg-slate-800/50 rounded p-2 text-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded">Ingestion</span>
                        <span className="text-xs text-slate-500">{err.source}</span>
                      </div>
                      <p className="text-orange-400 text-xs font-mono break-all">{err.errors || 'Validation failed'}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Recent Bets</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {bets?.bets?.length > 0 ? bets.bets.slice(0, 5).map((bet, i) => (
                  <div key={i} className="flex justify-between items-center py-2 border-b border-slate-700/50 last:border-0">
                    <div>
                      <p className="font-medium text-sm">{bet.market_name || 'Unknown'}</p>
                      <p className="text-xs text-slate-400">{bet.outcome_name}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-mono ${bet.result === 'win' ? 'text-emerald-400' : bet.result === 'loss' ? 'text-red-400' : 'text-slate-400'}`}>
                        {bet.result === 'win' ? `+$${bet.payout?.toFixed(2)}` : bet.result === 'loss' ? `-$${bet.stake?.toFixed(2)}` : 'Pending'}
                      </p>
                      <p className="text-xs text-slate-500">{bet.odds}x</p>
                    </div>
                  </div>
                )) : (
                  <EmptyState 
                    icon={TrendingUp} 
                    title="No Bets Yet" 
                    description="Place bets to see them here"
                  />
                )}
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Database Stats</h3>
              {dbStats && Object.keys(dbStats).length > 0 ? (
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(dbStats).map(([key, value]) => (
                    <div key={key} className="bg-slate-700/30 rounded-lg p-3">
                      <div className="flex items-center gap-1">
                        <Tooltip text={dbStatTooltips[key] || `Number of ${key.replace(/_/g, ' ')}`}>
                          <HelpCircle size={12} className="text-slate-500" />
                        </Tooltip>
                        <p className="text-xs text-slate-400 capitalize">{key.replace(/_/g, ' ')}</p>
                      </div>
                      <p className="text-lg font-mono">{typeof value === 'number' ? value.toLocaleString() : value}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState 
                  icon={Database} 
                  title="No Data Yet" 
                  description="Database statistics will appear here"
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Betting Tab */}
      {activeTab === 'betting' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Betting Performance</h2>
            <a href="/api/bets/export?format=csv" className="btn-secondary flex items-center gap-2">
              <Download size={16} /> Export CSV
            </a>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Bet History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-400 border-b border-slate-700">
                    <th className="pb-3">Market</th>
                    <th className="pb-3">Outcome</th>
                    <th className="pb-3">Odds</th>
                    <th className="pb-3">Stake</th>
                    <th className="pb-3">Result</th>
                    <th className="pb-3">Payout</th>
                  </tr>
                </thead>
                <tbody>
                  {bets?.bets?.map((bet, i) => (
                    <tr key={i} className="border-b border-slate-700/50">
                      <td className="py-3">{bet.market_name || '-'}</td>
                      <td className="py-3">{bet.outcome_name || '-'}</td>
                      <td className="py-3 font-mono">{bet.odds}</td>
                      <td className="py-3 font-mono">${bet.stake?.toFixed(2)}</td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs ${bet.result === 'win' ? 'bg-emerald-500/20 text-emerald-400' : bet.result === 'loss' ? 'bg-red-500/20 text-red-400' : 'bg-slate-700 text-slate-400'}`}>
                          {bet.result}
                        </span>
                      </td>
                      <td className="py-3 font-mono">${bet.payout?.toFixed(2) || '0.00'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Automation Tab */}
      {activeTab === 'automation' && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Automation Control</h3>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${status?.running ? 'bg-sky-500/20 text-sky-400' : 'bg-slate-700 text-slate-400'}`}>
                {status?.running ? 'Running' : 'Stopped'}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-slate-700/30 rounded-lg p-4">
                <p className="text-sm text-slate-400">Current Task</p>
                <p className="font-medium">{status?.current_task || 'None'}</p>
              </div>
              <div className="bg-slate-700/30 rounded-lg p-4">
                <p className="text-sm text-slate-400">Last Collection</p>
                <p className="font-medium font-mono text-sm">{status?.last_collection || 'Never'}</p>
              </div>
              <div className="bg-slate-700/30 rounded-lg p-4">
                <p className="text-sm text-slate-400">Last Training</p>
                <p className="font-medium font-mono text-sm">{status?.last_training || 'Never'}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <Tooltip text={taskButtonTooltip}>
                <button
                  onClick={() => triggerMutation.mutate('collect')}
                  disabled={triggerMutation.isPending || isTaskRunning}
                  className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play size={16} /> Run Collection
                </button>
              </Tooltip>
              <Tooltip text={taskButtonTooltip}>
                <button
                  onClick={() => triggerMutation.mutate('train')}
                  disabled={triggerMutation.isPending || isTaskRunning}
                  className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RefreshCw size={16} /> Run Training
                </button>
              </Tooltip>
              <Tooltip text={stopButtonTooltip}>
                <button
                  onClick={() => stopMutation.mutate()}
                  disabled={!isTaskRunning || stopMutation.isPending}
                  className="btn-danger flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Square size={16} /> Stop
                </button>
              </Tooltip>
            </div>
          </div>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="text-lg font-semibold">Model Versions</h3>
              <Tooltip text="Cross-Validation (CV) Score: Measures model accuracy using k-fold cross-validation. Higher scores (closer to 1.0) indicate better predictive performance. Each model is evaluated on multiple data folds to ensure reliability.">
                <HelpCircle size={16} className="text-slate-500 cursor-help" />
              </Tooltip>
            </div>
            <div className="space-y-4">
              {models?.versions?.length > 0 ? models.versions.map((model, i) => {
                const marketDescriptions = {
                  '1x2': 'Match Result: Predicts the match outcome - Home Win (1), Draw (X), or Away Win (2)',
                  'over_under': 'Total Goals: Predicts if the total number of goals scored by both teams will be Over 2.5 or Under 2.5',
                  'btts': 'Both Teams To Score (BTTS): Predicts whether both teams will score at least one goal each (Yes) or if at least one team fails to score (No)'
                }
                const description = marketDescriptions[model.market] || 'Betting market prediction model'
                
                return (
                  <div key={i} className={`p-4 rounded-lg border ${model.is_active ? 'border-sky-500/50 bg-sky-500/10' : 'border-slate-700 bg-slate-700/30'}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{model.market}</p>
                          <Tooltip text={description}>
                            <HelpCircle size={14} className="text-slate-500 cursor-help" />
                          </Tooltip>
                          {model.is_active && <span className="text-xs bg-sky-500 text-white px-2 py-0.5 rounded">Active</span>}
                        </div>
                        <p className="text-sm text-slate-400">Version {model.version_id}</p>
                        <p className="text-xs text-slate-500 mt-1">{description}</p>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <p className="font-mono">{model.cv_score?.toFixed(4) || '-'}</p>
                          <Tooltip text="Cross-Validation Score: Model accuracy measured using k-fold cross-validation. Values range from 0.0 to 1.0, with higher scores indicating better predictive performance.">
                            <HelpCircle size={12} className="text-slate-500 cursor-help" />
                          </Tooltip>
                        </div>
                        <p className="text-xs text-slate-400">CV Score</p>
                      </div>
                    </div>
                    <div className="mt-3 flex gap-4 text-sm text-slate-400">
                      <span>Samples: {model.training_samples}</span>
                      <span>Trained: {model.trained_at?.split('T')[0]}</span>
                    </div>
                  </div>
                )
              }) : (
                <EmptyState 
                  icon={RefreshCw} 
                  title="No Models Yet" 
                  description="Train models to see them here"
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Recent Logs</h3>
              <div className="flex items-center gap-2">
                <div className={`flex items-center gap-2 px-2 py-1 rounded text-xs ${wsConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  {wsConnected ? 'Live' : 'Disconnected'}
                </div>
                {!autoScroll && (
                  <button 
                    onClick={() => setAutoScroll(true)}
                    className="px-2 py-1 rounded text-xs bg-sky-500/20 text-sky-400 hover:bg-sky-500/30"
                  >
                    Resume Auto-scroll
                  </button>
                )}
              </div>
            </div>
            <div 
              ref={logsContainerRef}
              onScroll={handleLogsScroll}
              className="font-mono text-sm space-y-1 max-h-[500px] overflow-y-auto bg-slate-900/50 rounded-lg p-4"
            >
              {wsLogs.length > 0 ? wsLogs.map((log, i) => (
                <div key={`${log.timestamp}-${i}`} className={getLogLevelColor(log.level)}>
                  <span className="text-slate-500">{log.timestamp}</span>{' '}
                  <span className={getLogLevelColor(log.level)}>[{log.level?.toUpperCase()}]</span>{' '}
                  {log.message}
                </div>
              )) : (
                <EmptyState 
                  icon={Inbox} 
                  title="No Logs Yet" 
                  description="Logs will appear here when automation runs"
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
