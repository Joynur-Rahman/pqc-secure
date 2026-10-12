import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { KeyManagement } from './KeyManagement'
import { keyService } from '../services/api'

vi.mock('../services/api', () => ({
  keyService: {
    getMyKeys: vi.fn(),
    register: vi.fn(),
    rotateKey: vi.fn(),
    revokeKey: vi.fn(),
  },
}))

describe('KeyManagement Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders header, tabs, and displays empty state when no keys exist', async () => {
    vi.mocked(keyService.getMyKeys).mockResolvedValueOnce({
      data: { keys: [], total: 0 },
    })

    render(<KeyManagement />)

    expect(screen.getByText(/Cryptographic Key Management/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /My Keys/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /\+ Register Key/i })).toBeDefined()

    await waitFor(() => {
      expect(screen.getByText(/No cryptographic keys found/i)).toBeDefined()
    })
  })

  it('renders list of keys with algorithm, version, and status badges', async () => {
    const mockKeys = [
      {
        id: '1',
        key_id: 'ml-kem-768:abcd1234efgh5678',
        algorithm: 'ml-kem-768',
        version: 1,
        status: 'active',
        created_at: '2026-10-13T00:00:00Z',
      },
      {
        id: '2',
        key_id: 'x25519:1122334455667788',
        algorithm: 'x25519',
        version: 2,
        status: 'superseded',
        created_at: '2026-10-13T01:00:00Z',
      },
    ]

    vi.mocked(keyService.getMyKeys).mockResolvedValueOnce({
      data: { keys: mockKeys, total: 2 },
    })

    render(<KeyManagement />)

    await waitFor(() => {
      expect(screen.getByText('ml-kem-768:abcd1234efgh5678')).toBeDefined()
      expect(screen.getByText('x25519:1122334455667788')).toBeDefined()
      expect(screen.getByText(/PQC : ML-KEM-768/i)).toBeDefined()
      expect(screen.getByText(/CLASSICAL : X25519/i)).toBeDefined()
      expect(screen.getByText('v1')).toBeDefined()
      expect(screen.getByText('v2')).toBeDefined()
    })
  })

  it('allows switching to register tab and generating client keypair', async () => {
    vi.mocked(keyService.getMyKeys).mockResolvedValueOnce({
      data: { keys: [], total: 0 },
    })

    render(<KeyManagement />)

    const registerTabBtn = screen.getByRole('button', { name: /\+ Register Key/i })
    fireEvent.click(registerTabBtn)

    expect(screen.getByText(/Cryptographic Paradigm/i)).toBeDefined()
    expect(screen.getByLabelText(/Algorithm/i)).toBeDefined()

    // Switch to Classical
    const classicalBtn = screen.getByRole('button', { name: /Classical Cryptography/i })
    fireEvent.click(classicalBtn)

    // Click Auto-generate keypair
    const autoGenBtn = screen.getByRole('button', { name: /Auto-generate keypair/i })
    fireEvent.click(autoGenBtn)

    const textarea = screen.getByPlaceholderText(/Paste Base64-encoded/i) as HTMLTextAreaElement
    expect(textarea.value.length).toBeGreaterThan(0)
  })

  it('submits registration successfully and refreshes key list', async () => {
    vi.mocked(keyService.getMyKeys)
      .mockResolvedValueOnce({ data: { keys: [], total: 0 } })
      .mockResolvedValueOnce({
        data: {
          keys: [
            {
              id: 'new-key',
              key_id: 'ml-kem-768:9999888877776666',
              algorithm: 'ml-kem-768',
              version: 1,
              status: 'active',
              created_at: '2026-10-13T02:00:00Z',
            },
          ],
          total: 1,
        },
      })

    vi.mocked(keyService.register).mockResolvedValueOnce({
      data: {
        id: 'new-key',
        key_id: 'ml-kem-768:9999888877776666',
        algorithm: 'ml-kem-768',
        version: 1,
        status: 'active',
        created_at: '2026-10-13T02:00:00Z',
      },
    })

    render(<KeyManagement />)

    fireEvent.click(screen.getByRole('button', { name: /\+ Register Key/i }))

    const textarea = screen.getByPlaceholderText(/Paste Base64-encoded/i)
    fireEvent.change(textarea, { target: { value: 'QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=' } })

    const submitBtn = screen.getByRole('button', { name: /^Register Key$/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(keyService.register).toHaveBeenCalledWith('ml-kem-768', 'QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=')
      expect(screen.getByText(/Successfully registered ml-kem-768 key!/i)).toBeDefined()
    })
  })

  it('handles key rotation dialog flow', async () => {
    const mockKey = {
      id: 'k1',
      key_id: 'ml-kem-768:test1234',
      algorithm: 'ml-kem-768',
      version: 1,
      status: 'active',
      created_at: '2026-10-13T00:00:00Z',
    }

    vi.mocked(keyService.getMyKeys).mockResolvedValue({
      data: { keys: [mockKey], total: 1 },
    })

    vi.mocked(keyService.rotateKey).mockResolvedValueOnce({
      data: {
        id: 'k2',
        key_id: 'ml-kem-768:test5678',
        algorithm: 'ml-kem-768',
        version: 2,
        status: 'active',
        created_at: '2026-10-13T01:00:00Z',
      },
    })

    render(<KeyManagement />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Rotate$/i })).toBeDefined()
    })

    // Click Rotate
    fireEvent.click(screen.getByRole('button', { name: /^Rotate$/i }))

    // Dialog appears
    expect(screen.getByRole('dialog')).toBeDefined()
    expect(screen.getByText(/Rotate Key: ml-kem-768:test1234/i)).toBeDefined()

    // Confirm Rotation
    const confirmBtn = screen.getByRole('button', { name: /Confirm Rotation/i })
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(keyService.rotateKey).toHaveBeenCalledWith('ml-kem-768:test1234')
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('handles key revocation dialog flow with reason', async () => {
    const mockKey = {
      id: 'k1',
      key_id: 'ed25519:testsig123',
      algorithm: 'ed25519',
      version: 1,
      status: 'active',
      created_at: '2026-10-13T00:00:00Z',
    }

    vi.mocked(keyService.getMyKeys).mockResolvedValue({
      data: { keys: [mockKey], total: 1 },
    })

    vi.mocked(keyService.revokeKey).mockResolvedValueOnce({
      data: {
        key_id: 'ed25519:testsig123',
        status: 'revoked',
        message: 'Key revoked successfully',
      },
    })

    render(<KeyManagement />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Revoke$/i })).toBeDefined()
    })

    // Click Revoke
    fireEvent.click(screen.getByRole('button', { name: /^Revoke$/i }))

    // Dialog appears
    expect(screen.getByRole('dialog')).toBeDefined()
    expect(screen.getByText(/Revoke Key: ed25519:testsig123/i)).toBeDefined()

    // Add reason
    const reasonInput = screen.getByLabelText(/Revocation Reason/i)
    fireEvent.change(reasonInput, { target: { value: 'Device compromised' } })

    // Confirm Revoke
    const confirmBtn = screen.getByRole('button', { name: /Confirm Revoke/i })
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(keyService.revokeKey).toHaveBeenCalledWith('ed25519:testsig123', 'Device compromised')
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })
})
