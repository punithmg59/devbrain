import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { X } from 'lucide-react'

export interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
  duration?: number
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (
    message: string,
    type?: Toast['type'],
    duration?: number
  ) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TYPE_STYLES: Record<Toast['type'], string> = {
  success: 'bg-green-900/90 text-green-100 border-green-700',
  error: 'bg-red-900/90 text-red-100 border-red-700',
  info: 'bg-blue-900/90 text-blue-100 border-blue-700',
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast
  onDismiss: (id: string) => void
}) {
  return (
    <div
      role="status"
      className={`flex items-center gap-3 px-4 py-2.5 rounded-full border shadow-lg animate-slide-in-right ${TYPE_STYLES[toast.type]}`}
    >
      <span className="text-sm">{toast.message}</span>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const ctx = useContext(ToastContext)
  if (!ctx || ctx.toasts.length === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 max-w-sm">
      {ctx.toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={ctx.removeToast} />
      ))}
    </div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(
    (message: string, type: Toast['type'] = 'info', duration = 3000) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
      setToasts((prev) => [...prev, { id, message, type, duration }])
      window.setTimeout(() => removeToast(id), duration)
    },
    [removeToast]
  )

  const value = useMemo(
    () => ({ toasts, addToast, removeToast }),
    [toasts, addToast, removeToast]
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return ctx
}
