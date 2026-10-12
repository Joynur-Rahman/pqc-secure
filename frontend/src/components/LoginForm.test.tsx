import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LoginForm from './LoginForm'
import * as AuthHook from '../hooks/useAuth'

const mockLogin = vi.fn()

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    loading: false,
    logout: vi.fn(),
    register: vi.fn(),
  }),
}))

function renderLoginForm(props = {}) {
  return render(
    <BrowserRouter>
      <LoginForm {...props} />
    </BrowserRouter>
  )
}

describe('LoginForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form elements', () => {
    renderLoginForm()
    expect(screen.getByLabelText(/email address/i)).toBeDefined()
    expect(screen.getByLabelText(/^password/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined()
  })

  it('displays client-side validation errors on empty submission', async () => {
    renderLoginForm()
    const submitBtn = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/email address is required/i)).toBeDefined()
      expect(screen.getByText(/password is required/i)).toBeDefined()
    })
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('validates email format', async () => {
    renderLoginForm()
    const emailInput = screen.getByLabelText(/email address/i)
    fireEvent.change(emailInput, { target: { value: 'not-an-email' } })

    const submitBtn = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeDefined()
    })
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('submits form successfully with valid inputs', async () => {
    const onSuccess = vi.fn()
    mockLogin.mockResolvedValueOnce(undefined)

    renderLoginForm({ onSuccess })
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/^password/i)

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123' } })

    const submitBtn = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'Password123')
      expect(onSuccess).toHaveBeenCalled()
    })
  })

  it('displays server error message on login failure', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid email or password'))

    renderLoginForm()
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/^password/i)

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'WrongPass123' } })

    const submitBtn = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined()
      expect(screen.getByText(/invalid email or password/i)).toBeDefined()
    })
  })

  it('toggles password visibility', () => {
    renderLoginForm()
    const passwordInput = screen.getByLabelText(/^password/i) as HTMLInputElement
    const toggleBtn = screen.getByRole('button', { name: /show password/i })

    expect(passwordInput.type).toBe('password')
    fireEvent.click(toggleBtn)
    expect(passwordInput.type).toBe('text')
    fireEvent.click(toggleBtn)
    expect(passwordInput.type).toBe('password')
  })
})
