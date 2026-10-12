import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FileList } from './FileList'
import { fileService } from '../services/api'

vi.mock('../services/api', () => ({
  fileService: {
    list: vi.fn(),
    download: vi.fn(),
  },
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
})
