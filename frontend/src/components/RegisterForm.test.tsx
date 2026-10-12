import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import RegisterForm from './RegisterForm'

const mockRegister = vi.fn()

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    register: mockRegister,
    user: null,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

function renderRegisterForm(props = {}) {
  return render(
    <BrowserRouter>
      <RegisterForm {...props} />
    </BrowserRouter>
  )
}

describe('RegisterForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders register form elements', () => {
    renderRegisterForm()
    expect(screen.getByLabelText(/email address/i)).toBeDefined()
    expect(screen.getByLabelText(/^password/i)).toBeDefined()
    expect(screen.getByLabelText(/confirm password/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /create account/i })).toBeDefined()
  })

  it('validates empty inputs on submission', async () => {
    renderRegisterForm()
    const submitBtn = screen.getByRole('button', { name: /create account/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/email address is required/i)).toBeDefined()
      expect(screen.getByText(/password is required/i)).toBeDefined()
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('validates password complexity', async () => {
    renderRegisterForm()
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/^password/i)
    const confirmInput = screen.getByLabelText(/confirm password/i)

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'simple' } })
    fireEvent.change(confirmInput, { target: { value: 'simple' } })

    const submitBtn = screen.getByRole('button', { name: /create account/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeDefined()
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('validates passwords match', async () => {
    renderRegisterForm()
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/^password/i)
    const confirmInput = screen.getByLabelText(/confirm password/i)

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'SecurePass123' } })
    fireEvent.change(confirmInput, { target: { value: 'MismatchPass999' } })

    const submitBtn = screen.getByRole('button', { name: /create account/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeDefined()
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('calls register on valid inputs', async () => {
    mockRegister.mockResolvedValueOnce({ id: '123', email: 'test@example.com' })

    renderRegisterForm()
    const emailInput = screen.getByLabelText(/email address/i)
    const passwordInput = screen.getByLabelText(/^password/i)
    const confirmInput = screen.getByLabelText(/confirm password/i)

    fireEvent.change(emailInput, { target: { value: 'newuser@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'ValidPass123' } })
    fireEvent.change(confirmInput, { target: { value: 'ValidPass123' } })

    const submitBtn = screen.getByRole('button', { name: /create account/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('newuser@example.com', 'ValidPass123')
      expect(screen.getByRole('status')).toBeDefined()
    })
  })
})
