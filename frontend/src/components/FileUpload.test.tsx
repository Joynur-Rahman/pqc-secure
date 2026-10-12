import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FileUpload } from './FileUpload'
import { fileService } from '../services/api'

vi.mock('../services/api', () => ({
  fileService: {
    upload: vi.fn(),
    share: vi.fn(),
  },
}))

describe('FileUpload Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload form elements, file input, and encryption mode selector', () => {
    render(<FileUpload />)

    expect(screen.getByText(/Post-Quantum File Encryption & Sharing/i)).toBeDefined()
    expect(screen.getByText(/Select File to Encrypt/i)).toBeDefined()
    expect(screen.getByText(/Post-Quantum Mode/i)).toBeDefined()
    expect(screen.getByText(/Classical Mode/i)).toBeDefined()
    expect(screen.getByLabelText(/Recipients/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /Encrypt & Share File/i })).toBeDefined()
  })

  it('adds and removes recipient email pills', async () => {
    render(<FileUpload />)

    const recipientInput = screen.getByLabelText(/Recipients/i)
    const addBtn = screen.getByRole('button', { name: /\+ Add/i })

    // Add first recipient
    fireEvent.change(recipientInput, { target: { value: 'bob@example.com' } })
    fireEvent.click(addBtn)

    expect(screen.getByText('bob@example.com')).toBeDefined()

    // Add second recipient
    fireEvent.change(recipientInput, { target: { value: 'alice@example.com' } })
    fireEvent.click(addBtn)

    expect(screen.getByText('alice@example.com')).toBeDefined()

    // Remove first recipient
    const removeBtns = screen.getAllByRole('button', { name: '×' })
    fireEvent.click(removeBtns[0])

    expect(screen.queryByText('bob@example.com')).toBeNull()
    expect(screen.getByText('alice@example.com')).toBeDefined()
  })

  it('validates invalid recipient email address', () => {
    render(<FileUpload />)

    const recipientInput = screen.getByLabelText(/Recipients/i)
    const addBtn = screen.getByRole('button', { name: /\+ Add/i })

    fireEvent.change(recipientInput, { target: { value: 'invalid-email-address' } })
    fireEvent.click(addBtn)

    expect(screen.getByText(/Please enter a valid email address/i)).toBeDefined()
  })

  it('allows switching between PQC and Classical encryption modes', () => {
    render(<FileUpload />)

    const classicalModeCard = screen.getByText(/Classical Mode/i)
    fireEvent.click(classicalModeCard)

    const pqcModeCard = screen.getByText(/Post-Quantum Mode/i)
    fireEvent.click(pqcModeCard)

    expect(screen.getByText(/ML-KEM-768 key encapsulation/i)).toBeDefined()
  })

  it('orchestrates complete upload and share encryption pipeline flow', async () => {
    vi.mocked(fileService.upload).mockResolvedValueOnce({
      data: {
        upload_id: 'test-upload-uuid-1234',
        filename: 'secret.pdf',
        chunk_number: 0,
        total_chunks: 1,
        bytes_uploaded: 1024,
        is_complete: true,
        message: 'Upload complete',
      },
    })

    vi.mocked(fileService.share).mockResolvedValueOnce({
      data: {
        id: 'pkg-98765-uuid',
        senderId: 'user-1',
        senderEmail: 'alice@example.com',
        recipients: ['bob@example.com'],
        fileName: 'secret.pdf',
        fileSize: 1024,
        encryptionMode: 'pqc',
        createdAt: '2026-10-13T00:00:00Z',
        status: 'shared',
      },
    })

    const handleSuccess = vi.fn()
    render(<FileUpload onSuccess={handleSuccess} />)

    // Select file
    const file = new File(['Dummy file content for test'], 'secret.pdf', { type: 'application/pdf' })
    const fileInput = document.getElementById('file-input') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    expect(screen.getByText(/Selected:/i)).toBeDefined()

    // Add recipient
    const recipientInput = screen.getByLabelText(/Recipients/i)
    fireEvent.change(recipientInput, { target: { value: 'bob@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /\+ Add/i }))

    // Submit share
    const submitBtn = screen.getByRole('button', { name: /Encrypt & Share File/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(fileService.upload).toHaveBeenCalled()
      expect(fileService.share).toHaveBeenCalledWith('test-upload-uuid-1234', ['bob@example.com'], 'pqc')
      expect(screen.getByText(/File Encrypted & Shared Successfully!/i)).toBeDefined()
      expect(screen.getByText('pkg-98765-uuid')).toBeDefined()
      expect(handleSuccess).toHaveBeenCalledWith('pkg-98765-uuid')
    })
  })
})
