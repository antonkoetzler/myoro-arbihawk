import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component to catch React errors and display them
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className='flex min-h-screen items-center justify-center bg-slate-900 p-8'>
          <div className='card max-w-2xl'>
            <h2 className='mb-4 text-xl font-bold text-red-400'>Something went wrong</h2>
            <div className='mb-4 space-y-2'>
              <p className='text-sm text-slate-300'>
                <strong>Error:</strong> {this.state.error?.message || 'Unknown error'}
              </p>
              {this.state.errorInfo && (
                <details className='mt-4'>
                  <summary className='cursor-pointer text-sm text-slate-400 hover:text-slate-300'>
                    Stack trace
                  </summary>
                  <pre className='mt-2 max-h-96 overflow-auto rounded bg-slate-800 p-4 text-xs text-slate-300'>
                    {this.state.error?.stack}
                    {'\n\n'}
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null, errorInfo: null });
                window.location.reload();
              }}
              className='btn-primary'
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
