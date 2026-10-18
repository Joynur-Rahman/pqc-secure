import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface RegisterFormProps {
  onSuccess?: () => void
}

export default function RegisterForm({ onSuccess }: RegisterFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string
    password?: string
    confirmPassword?: string
  }>({})
  const [loading, setLoading] = useState(false)

  const { register } = useAuth()
  const navigate = useNavigate()

  // Real-time password criteria
  const hasLength = password.length >= 8
  const hasUpper = /[A-Z]/.test(password)
  const hasLower = /[a-z]/.test(password)
  const hasDigit = /[0-9]/.test(password)

  function validate(): boolean {
    const errors: { email?: string; password?: string; confirmPassword?: string } = {}
    const trimmedEmail = email.trim()

    if (!trimmedEmail) {
      errors.email = 'Email address is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = 'Please enter a valid email address'
    }

    if (!password) {
      errors.password = 'Password is required'
    } else if (!(hasLength && hasUpper && hasLower && hasDigit)) {
      errors.password =
        'Password must be at least 8 characters and include uppercase, lowercase, and numbers'
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccessMessage('')

    if (!validate()) {
      return
    }

    setLoading(true)

    try {
      await register(email.trim().toLowerCase(), password)
      setSuccessMessage('Account created successfully! Redirecting to login...')
      setTimeout(() => {
        if (onSuccess) {
          onSuccess()
        } else {
          navigate('/login')
        }
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div data-ui="register-form" className="w-full max-w-md mx-auto p-8 pqc-card space-y-6">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold tracking-tight text-white">Create Account</h2>
        <p className="text-xs text-neutral-400">Get started with Post-Quantum Cryptography</p>
      </div>

      {error && (
        <div
          role="alert"
          className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start gap-2"
        >
          <svg className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-300 flex items-start gap-2"
        >
          <svg className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="space-y-1.5">
          <label htmlFor="reg-email" className="block text-xs font-semibold text-neutral-300">
            Email address
          </label>
          <input
            id="reg-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              if (fieldErrors.email) setFieldErrors({ ...fieldErrors, email: undefined })
            }}
            className={`pqc-input text-xs ${
              fieldErrors.email ? 'border-rose-500 focus:border-rose-400' : ''
            }`}
            placeholder="alice@example.com"
          />
          {fieldErrors.email && (
            <p className="text-[11px] text-rose-400">{fieldErrors.email}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <label htmlFor="reg-password" className="block text-xs font-semibold text-neutral-300">
            Password
          </label>
          <div className="relative">
            <input
              id="reg-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                if (fieldErrors.password) setFieldErrors({ ...fieldErrors, password: undefined })
              }}
              className={`pqc-input text-xs pr-16 ${
                fieldErrors.password ? 'border-rose-500 focus:border-rose-400' : ''
              }`}
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs text-neutral-400 hover:text-white transition-colors cursor-pointer"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {fieldErrors.password && (
            <p className="text-[11px] text-rose-400">{fieldErrors.password}</p>
          )}

          {/* Password complexity indicator */}
          <div className="mt-2 text-xs space-y-1.5 bg-[#0c0d0e]/60 p-3 rounded-lg border border-white/[0.06]">
            <p className="font-semibold text-neutral-300 text-[11px]">Password Requirements:</p>
            <div className="grid grid-cols-2 gap-1.5 text-[11px]">
              <span className={hasLength ? 'text-emerald-400 font-medium flex items-center gap-1' : 'text-neutral-400 flex items-center gap-1'}>
                <span className="w-1.5 h-1.5 rounded-full inline-block bg-current shrink-0"></span> At least 8 characters
              </span>
              <span className={hasUpper ? 'text-emerald-400 font-medium flex items-center gap-1' : 'text-neutral-400 flex items-center gap-1'}>
                <span className="w-1.5 h-1.5 rounded-full inline-block bg-current shrink-0"></span> Uppercase letter
              </span>
              <span className={hasLower ? 'text-emerald-400 font-medium flex items-center gap-1' : 'text-neutral-400 flex items-center gap-1'}>
                <span className="w-1.5 h-1.5 rounded-full inline-block bg-current shrink-0"></span> Lowercase letter
              </span>
              <span className={hasDigit ? 'text-emerald-400 font-medium flex items-center gap-1' : 'text-neutral-400 flex items-center gap-1'}>
                <span className="w-1.5 h-1.5 rounded-full inline-block bg-current shrink-0"></span> Numeric digit
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="reg-confirm-password" className="block text-xs font-semibold text-neutral-300">
            Confirm Password
          </label>
          <input
            id="reg-confirm-password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value)
              if (fieldErrors.confirmPassword)
                setFieldErrors({ ...fieldErrors, confirmPassword: undefined })
            }}
            className={`pqc-input text-xs ${
              fieldErrors.confirmPassword ? 'border-rose-500 focus:border-rose-400' : ''
            }`}
            placeholder="••••••••"
          />
          {fieldErrors.confirmPassword && (
            <p className="text-[11px] text-rose-400">{fieldErrors.confirmPassword}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="pqc-btn-primary w-full py-2.5 text-xs font-semibold mt-2"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="pqc-dot-pulse"></span>
              <span>Creating account...</span>
            </span>
          ) : (
            'Create Account'
          )}
        </button>
      </form>

      <div className="pt-3 text-center text-xs text-neutral-400">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-emerald-400 hover:text-emerald-300 transition-colors">
          Sign in
        </Link>
      </div>
    </div>
  )
}
