import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FileList } from './FileList'
import { fileService } from '../services/api'
import * as AuthHook from '../hooks/useAuth'

vi.mock('../services/api', () => ({
  fileService: {
    list: vi.fn(),
    download: vi.fn(),
    revokeGrant: vi.fn(),
  },
}))

vi.mock('../hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    user: { id: 'user-alice', email: 'alice@example.com' },
    loading: false,
  })),
}))

describe('FileList and Decryption Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = vi.fn()
  })

  it('renders loading state initially and then displays shared files', async () => {
    const mockFiles = [
      {
        id: 'pkg-1',
        package_id: 'pkg-1',
        original_filename: 'financial_records.pdf',
        file_size: 1048576,
        crypto_mode: 'pqc',
        package_version: '1.0',
        sender_id: 'user-alice',
        sender_email: 'alice@example.com',
        created_at: '2026-10-12T12:00:00Z',
        status: 'active',
      },
    ]

    vi.mocked(fileService.list).mockResolvedValueOnce({
      data: { packages: mockFiles, total: 1 } as any,
    })

    render(<FileList />)

    expect(screen.getByText(/Loading shared packages/i)).toBeDefined()

    await waitFor(() => {
      expect(screen.getByText('financial_records.pdf')).toBeDefined()
      expect(screen.getByText(/NIST PQC \(ML-KEM \/ ML-DSA\)/i)).toBeDefined()
      expect(screen.getByText(/alice@example.com/i)).toBeDefined()
    })
  })

  it('displays empty state when no files are shared', async () => {
    vi.mocked(fileService.list).mockResolvedValueOnce({
      data: { packages: [], total: 0 } as any,
    })

    render(<FileList />)

    await waitFor(() => {
      expect(screen.getByTestId('no-files-message')).toBeDefined()
      expect(screen.getByText(/No shared files found/i)).toBeDefined()
    })
  })

  it('handles successful file decryption and download trigger', async () => {
    const mockFiles = [
      {
        id: 'pkg-pqc-1',
        package_id: 'pkg-pqc-1',
        original_filename: 'quantum_secrets.txt',
        file_size: 2048,
        crypto_mode: 'pqc',
        package_version: '1.0',
        sender_id: 'user-alice',
        sender_email: 'alice@example.com',
        created_at: '2026-10-12T12:00:00Z',
        status: 'active',
      },
    ]

    vi.mocked(fileService.list).mockResolvedValueOnce({
      data: { packages: mockFiles, total: 1 } as any,
    })

    const mockBlob = new Blob(['decrypted secret plaintext'], { type: 'text/plain' })
    vi.mocked(fileService.download).mockResolvedValueOnce({
      blob: mockBlob,
      filename: 'quantum_secrets.txt',
    })

    render(<FileList />)

    await waitFor(() => {
      expect(screen.getByText('quantum_secrets.txt')).toBeDefined()
    })

    const downloadBtn = screen.getByTestId('download-button-pkg-pqc-1')
    fireEvent.click(downloadBtn)

    await waitFor(() => {
      expect(fileService.download).toHaveBeenCalledWith('pkg-pqc-1')
      expect(screen.getByTestId('success-pkg-pqc-1')).toBeDefined()
      expect(screen.getByText(/Decrypted and verified successfully/i)).toBeDefined()
    })
  })

  it('displays error message gracefully when decryption fails', async () => {
    const mockFiles = [
      {
        id: 'pkg-bad-sig',
        package_id: 'pkg-bad-sig',
        original_filename: 'corrupted_file.txt',
        file_size: 512,
        crypto_mode: 'classical',
        package_version: '1.0',
        sender_id: 'user-bob',
        sender_email: 'bob@example.com',
        created_at: '2026-10-12T12:00:00Z',
        status: 'active',
      },
    ]

    vi.mocked(fileService.list).mockResolvedValueOnce({
      data: { packages: mockFiles, total: 1 } as any,
    })

    vi.mocked(fileService.download).mockResolvedValueOnce({
      error: 'Security alert: Package signature failed verification. File may be tampered.',
    })

    render(<FileList />)

    await waitFor(() => {
      expect(screen.getByText('corrupted_file.txt')).toBeDefined()
    })

    const downloadBtn = screen.getByTestId('download-button-pkg-bad-sig')
    fireEvent.click(downloadBtn)

    await waitFor(() => {
      expect(screen.getByTestId('error-pkg-bad-sig')).toBeDefined()
      expect(
        screen.getByText(/Security alert: Package signature failed verification/i)
      ).toBeDefined()
    })
  })

  describe('Phase 6 Revocation UI (Task 6.3)', () => {
    const sharedPackageWithRecipients = {
      id: 'pkg-rev-101',
      package_id: 'pkg-rev-101',
      original_filename: 'defense_contract.pdf',
      file_size: 4096,
      crypto_mode: 'pqc',
      package_version: '1.0',
      sender_id: 'user-alice',
      sender_email: 'alice@example.com',
      recipients: [
        {
          recipient_id: 'user-bob',
          recipient_email: 'bob@example.com',
          recipient_key_id: 'ml-kem-768:key-bob-1',
          grant_id: 'grant-bob-101',
          status: 'active',
        },
      ],
      created_at: '2026-10-15T10:00:00Z',
      status: 'active',
    }

    it('renders recipient access list and active status badge for sender', async () => {
      vi.mocked(fileService.list).mockResolvedValueOnce({
        data: { packages: [sharedPackageWithRecipients], total: 1 } as any,
      })

      render(<FileList />)

      await waitFor(() => {
        expect(screen.getByText('defense_contract.pdf')).toBeDefined()
        expect(screen.getByText('Sent by you')).toBeDefined()
        expect(screen.getByText(/Recipients & Access Control \(1\)/i)).toBeDefined()
        expect(screen.getByText('bob@example.com')).toBeDefined()
        expect(screen.getByTestId('status-badge-active-grant-bob-101')).toBeDefined()
        expect(screen.getByTestId('revoke-btn-grant-bob-101')).toBeDefined()
      })
    })

    it('opens confirmation modal with warning and recipient details on revoke click', async () => {
      vi.mocked(fileService.list).mockResolvedValueOnce({
        data: { packages: [sharedPackageWithRecipients], total: 1 } as any,
      })

      render(<FileList />)

      await waitFor(() => {
        expect(screen.getByTestId('revoke-btn-grant-bob-101')).toBeDefined()
      })

      // Click revoke button
      fireEvent.click(screen.getByTestId('revoke-btn-grant-bob-101'))

      // Modal should appear
      await waitFor(() => {
        expect(screen.getByTestId('revoke-confirmation-modal')).toBeDefined()
        expect(screen.getByText('Confirm Share Revocation')).toBeDefined()
        expect(screen.getByText(/Are you sure you want to revoke access for/i)).toBeDefined()
        expect(screen.getByTestId('cancel-revoke-btn')).toBeDefined()
        expect(screen.getByTestId('confirm-revoke-btn')).toBeDefined()
      })
    })

    it('dismisses confirmation modal when cancel button is clicked', async () => {
      vi.mocked(fileService.list).mockResolvedValueOnce({
        data: { packages: [sharedPackageWithRecipients], total: 1 } as any,
      })

      render(<FileList />)

      await waitFor(() => {
        expect(screen.getByTestId('revoke-btn-grant-bob-101')).toBeDefined()
      })

      fireEvent.click(screen.getByTestId('revoke-btn-grant-bob-101'))
      expect(screen.getByTestId('revoke-confirmation-modal')).toBeDefined()

      // Click cancel
      fireEvent.click(screen.getByTestId('cancel-revoke-btn'))

      await waitFor(() => {
        expect(screen.queryByTestId('revoke-confirmation-modal')).toBeNull()
      })
    })

    it('successfully revokes grant, updates UI status to REVOKED, and shows toast', async () => {
      vi.mocked(fileService.list).mockResolvedValueOnce({
        data: { packages: [sharedPackageWithRecipients], total: 1 } as any,
      })
      vi.mocked(fileService.revokeGrant).mockResolvedValueOnce({} as any)

      render(<FileList />)

      await waitFor(() => {
        expect(screen.getByTestId('revoke-btn-grant-bob-101')).toBeDefined()
      })

      // Open modal
      fireEvent.click(screen.getByTestId('revoke-btn-grant-bob-101'))

      // Confirm revocation
      const confirmBtn = screen.getByTestId('confirm-revoke-btn')
      fireEvent.click(confirmBtn)

      await waitFor(() => {
        expect(fileService.revokeGrant).toHaveBeenCalledWith('pkg-rev-101', 'grant-bob-101')
        expect(screen.queryByTestId('revoke-confirmation-modal')).toBeNull()
        expect(screen.getByTestId('status-badge-revoked-grant-bob-101')).toBeDefined()
        expect(screen.getByText('REVOKED')).toBeDefined()
        expect(screen.getByText('Access Revoked')).toBeDefined()
        expect(screen.getByTestId('success-toast')).toBeDefined()
        expect(
          screen.getByText(/Access for bob@example.com has been successfully revoked/i)
        ).toBeDefined()
      })
    })
  })
})

