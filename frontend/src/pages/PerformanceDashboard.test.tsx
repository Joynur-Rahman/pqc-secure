import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import PerformanceDashboard from './PerformanceDashboard'
import { perfService } from '../services/api'
import { BenchmarkResponse, EnvironmentMetadata } from '../types'

vi.mock('../services/api', () => ({
  perfService: {
    getEnvironment: vi.fn(),
    getLatest: vi.fn(),
    runBenchmark: vi.fn(),
  },
}))

const mockEnv: EnvironmentMetadata = {
  cpu_model: 'Intel Core i9-12900K',
  cpu_cores: 16,
  total_ram_gb: 32.0,
  os_name: 'Windows',
  os_version: '11',
  architecture: 'AMD64',
  python_version: '3.14.3',
  cryptography_version: '44.0.0',
  pqc_backend: 'ML-KEM & ML-DSA Engine (liboqs)',
  environment_notice: 'Measurements are host-dependent.',
}

const mockBenchmark: BenchmarkResponse = {
  id: 'bench-test-1234',
  timestamp: '2026-10-18T10:00:00Z',
  iterations: 10,
  environment: mockEnv,
  summary: {
    pqc_total_time_ms: 25.4,
    classical_total_time_ms: 10.2,
    time_ratio: 2.49,
    key_size_overhead_ratio: 37.0,
    signature_size_overhead_ratio: 51.7,
  },
  results: [
    {
      operation: 'Keypair Generation',
      algorithm: 'ML-KEM-768',
      mode: 'pqc',
      category: 'key_generation',
      timing: {
        median_ms: 12.3,
        p90_ms: 14.1,
        p95_ms: 15.0,
        p99_ms: 16.0,
        min_ms: 11.0,
        max_ms: 17.0,
        mean_ms: 12.5,
        std_dev_ms: 1.2,
        iterations: 10,
      },
      sizes: {
        public_key_bytes: 1184,
        private_key_bytes: 2400,
      },
    },
    {
      operation: 'Keypair Generation',
      algorithm: 'X25519',
      mode: 'classical',
      category: 'key_generation',
      timing: {
        median_ms: 1.2,
        p90_ms: 1.5,
        p95_ms: 1.6,
        p99_ms: 1.8,
        min_ms: 1.0,
        max_ms: 2.0,
        mean_ms: 1.3,
        std_dev_ms: 0.2,
        iterations: 10,
      },
      sizes: {
        public_key_bytes: 32,
        private_key_bytes: 32,
      },
    },
    {
      operation: 'Signing',
      algorithm: 'ML-DSA-65',
      mode: 'pqc',
      category: 'signatures',
      timing: {
        median_ms: 8.5,
        p90_ms: 9.0,
        p95_ms: 9.5,
        p99_ms: 10.0,
        min_ms: 8.0,
        max_ms: 10.5,
        mean_ms: 8.6,
        std_dev_ms: 0.5,
        iterations: 10,
      },
      sizes: {
        signature_bytes: 3309,
        public_key_bytes: 1952,
      },
    },
    {
      operation: 'Encryption (1 KB)',
      algorithm: 'AES-256-GCM',
      mode: 'symmetric',
      category: 'symmetric_encryption',
      payload_size_bytes: 1024,
      timing: {
        median_ms: 0.15,
        p90_ms: 0.2,
        p95_ms: 0.25,
        p99_ms: 0.3,
        min_ms: 0.1,
        max_ms: 0.35,
        mean_ms: 0.16,
        std_dev_ms: 0.03,
        iterations: 10,
      },
      sizes: {
        ciphertext_bytes: 1040,
        overhead_bytes: 28,
      },
      throughput_mb_s: 250.0,
    },
  ],
}

describe('PerformanceDashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  it('renders title, environment specs, and executive summary metrics', async () => {
    vi.mocked(perfService.getEnvironment).mockResolvedValueOnce({ data: mockEnv })
    vi.mocked(perfService.getLatest).mockResolvedValueOnce({ data: mockBenchmark })

    render(<PerformanceDashboard />)

    expect(screen.getByText(/Performance Measurement & Evaluation/i)).toBeDefined()

    await waitFor(() => {
      expect(screen.getByText(/Intel Core i9-12900K/i)).toBeDefined()
      expect(screen.getByText(/25.40 ms/i)).toBeDefined()
      expect(screen.getByText(/1,184 Bytes/i)).toBeDefined()
      expect(screen.getAllByText(/3,309 Bytes/i).length).toBeGreaterThan(0)
      expect(screen.getByText(/2.49x/i)).toBeDefined()
    })
  })

  it('filters results table by category tabs', async () => {
    vi.mocked(perfService.getEnvironment).mockResolvedValueOnce({ data: mockEnv })
    vi.mocked(perfService.getLatest).mockResolvedValueOnce({ data: mockBenchmark })

    render(<PerformanceDashboard />)

    await waitFor(() => {
      expect(screen.getAllByText(/ML-KEM-768/i).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/AES-256-GCM/i).length).toBeGreaterThan(0)
    })

    // Click 'Signatures' tab
    const sigTab = screen.getByRole('button', { name: /Digital Signatures/i })
    fireEvent.click(sigTab)

    const tbodyAfterSig = document.querySelector('tbody')
    expect(tbodyAfterSig?.textContent).toContain('ML-DSA-65')
    expect(tbodyAfterSig?.textContent).not.toContain('AES-256-GCM')

    // Click 'Symmetric Encryption' tab
    const symTab = screen.getByRole('button', { name: /Symmetric Encryption/i })
    fireEvent.click(symTab)

    const tbodyAfterSym = document.querySelector('tbody')
    expect(tbodyAfterSym?.textContent).toContain('AES-256-GCM')
    expect(tbodyAfterSym?.textContent).not.toContain('ML-DSA-65')
  })

  it('executes benchmark suite when button is clicked', async () => {
    vi.mocked(perfService.getEnvironment).mockResolvedValueOnce({ data: mockEnv })
    vi.mocked(perfService.getLatest).mockResolvedValueOnce({ data: mockBenchmark })
    vi.mocked(perfService.runBenchmark).mockResolvedValueOnce({ data: mockBenchmark })

    render(<PerformanceDashboard />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Run Benchmark Suite/i })).toBeDefined()
    })

    const runBtn = screen.getByRole('button', { name: /Run Benchmark Suite/i })
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(perfService.runBenchmark).toHaveBeenCalledTimes(1)
    })
  })

  it('handles JSON and CSV exports', async () => {
    vi.mocked(perfService.getEnvironment).mockResolvedValueOnce({ data: mockEnv })
    vi.mocked(perfService.getLatest).mockResolvedValueOnce({ data: mockBenchmark })

    render(<PerformanceDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/Export JSON/i)).toBeDefined()
    })

    const jsonBtn = screen.getByText(/Export JSON/i)
    fireEvent.click(jsonBtn)
    expect(window.URL.createObjectURL).toHaveBeenCalled()

    const csvBtn = screen.getByText(/Export CSV/i)
    fireEvent.click(csvBtn)
    expect(window.URL.createObjectURL).toHaveBeenCalled()
  })
})
