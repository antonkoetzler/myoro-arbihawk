import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  type ReactNode,
} from 'react';
import { AlertCircle, X } from 'lucide-react';
import type { ToastType } from '../types';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

type ToastContextType = (message: string, type?: ToastType, duration?: number) => void;

const ToastContext = createContext<ToastContextType | null>(null);

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timeoutsRef = useRef<Map<number, NodeJS.Timeout>>(new Map());

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((timeout) => clearTimeout(timeout));
      timeoutsRef.current.clear();
    };
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'error', duration: number = 3000) => {
      const id = Date.now();
      setToasts((prev) => [...prev, { id, message, type }]);
      
      const timeoutId = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
        timeoutsRef.current.delete(id);
      }, duration);
      
      timeoutsRef.current.set(id, timeoutId);
    },
    []
  );

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div className='fixed right-4 top-4 z-50 space-y-2'>
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex min-w-[300px] items-center gap-3 rounded-lg px-4 py-3 shadow-lg ${
              toast.type === 'error'
                ? 'bg-red-500/90 text-white'
                : toast.type === 'success'
                  ? 'bg-emerald-500/90 text-white'
                  : 'bg-slate-700/90 text-white'
            }`}
          >
            <AlertCircle size={20} />
            <span className='flex-1 text-sm'>{toast.message}</span>
            <button
              onClick={() =>
                setToasts((prev) => prev.filter((t) => t.id !== toast.id))
              }
              className='opacity-70 hover:opacity-100'
              type='button'
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
