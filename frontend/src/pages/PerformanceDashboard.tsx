import React, { useState, useEffect } from 'react'
import {
  BenchmarkResponse,
  BenchmarkItem,
  EnvironmentMetadata,
} from '../types'
import { perfService } from '../services/api'

export default function PerformanceDashboard() {
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkResponse | null>(null)
  const [environment, setEnvironment] = useState<EnvironmentMetadata | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [running, setRunning] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string>('all')

  // Benchmark Run Parameters
  const [iterations, setIterations] = useState<number>(10)
  const [selectedSizePreset, setSelectedSizePreset] = useState<string>('standard')
  const [includePqc, setIncludePqc] = useState<boolean>(true)
  const [includeClassical, setIncludeClassical] = useState<boolean>(true)

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [envRes, latestRes] = await Promise.all([
        perfService.getEnvironment(),
        perfService.getLatest(),
      ])

      if (envRes.data) {
        setEnvironment(envRes.data)
      }

      if (latestRes.data && latestRes.data.results && latestRes.data.results.length > 0) {
        setBenchmarkData(latestRes.data)
      } else {
        // Run initial light benchmark if no cached run exists
        const runRes = await perfService.runBenchmark({ iterations: 5, file_sizes_kb: [1, 64] })
        if (runRes.data) {
          setBenchmarkData(runRes.data)
          if (!envRes.data && runRes.data.environment) {
            setEnvironment(runRes.data.environment)
          }
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load performance metrics')
    } finally {
      setLoading(false)
    }
  }

  const handleRunBenchmark = async () => {
    setRunning(true)
    setError(null)
    try {
      let fileSizes = [1, 64]
      if (selectedSizePreset === 'quick') fileSizes = [1]
      else if (selectedSizePreset === 'heavy') fileSizes = [1, 64, 1024]

      const res = await perfService.runBenchmark({
        iterations,
        file_sizes_kb: fileSizes,
        include_pqc: includePqc,
        include_classical: includeClassical,
      })

      if (res.error) {
        setError(res.error)
      } else if (res.data) {
        setBenchmarkData(res.data)
        if (res.data.environment) {
          setEnvironment(res.data.environment)
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Benchmark execution failed')
    } finally {
      setRunning(false)
    }
  }

  // Export results to JSON
  const handleExportJson = () => {
    if (!benchmarkData) return
    const jsonStr = JSON.stringify(benchmarkData, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pqc_benchmark_report_${benchmarkData.id || Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Export results to CSV
  const handleExportCsv = () => {
    if (!benchmarkData || !benchmarkData.results) return

    const headers = [
      'Operation',
      'Algorithm',
      'Mode',
      'Category',
      'Payload (Bytes)',
      'Median (ms)',
      'P90 (ms)',
      'P95 (ms)',
      'Min (ms)',
      'Max (ms)',
      'Mean (ms)',
      'StdDev (ms)',
      'Public Key (Bytes)',
      'Private Key (Bytes)',
      'Ciphertext (Bytes)',
      'Signature (Bytes)',
      'Shared Secret (Bytes)',
      'Overhead (Bytes)',
      'Throughput (MB/s)',
    ]

    const rows = benchmarkData.results.map((r: BenchmarkItem) => [
      `"${r.operation}"`,
      `"${r.algorithm}"`,
      r.mode,
      r.category,
      r.payload_size_bytes ?? '',
      r.timing.median_ms.toFixed(4),
      r.timing.p90_ms.toFixed(4),
      r.timing.p95_ms.toFixed(4),
      r.timing.min_ms.toFixed(4),
      r.timing.max_ms.toFixed(4),
      r.timing.mean_ms.toFixed(4),
      r.timing.std_dev_ms.toFixed(4),
      r.sizes.public_key_bytes ?? '',
      r.sizes.private_key_bytes ?? '',
      r.sizes.ciphertext_bytes ?? '',
      r.sizes.signature_bytes ?? '',
      r.sizes.shared_secret_bytes ?? '',
      r.sizes.overhead_bytes ?? '',
      r.throughput_mb_s ?? '',
    ])

    const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pqc_benchmark_report_${benchmarkData.id || Date.now()}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const filteredResults = benchmarkData?.results.filter((item: BenchmarkItem) => {
    if (activeCategory === 'all') return true
    return item.category === activeCategory
  }) || []

  const activeEnv = environment || benchmarkData?.environment

  return (
    <div data-ui="performance-dashboard" className="space-y-8 pb-12 max-w-7xl mx-auto px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-white">
              Performance Measurement & Evaluation
            </h1>
            <span className="pqc-badge pqc-badge-quantum text-[10px] py-0.5">Empirical Telemetry</span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Empirical benchmarking of Post-Quantum Cryptography (ML-KEM-768, ML-DSA-65) vs. Classical (X25519, Ed25519) and AES-256-GCM.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportJson}
            disabled={!benchmarkData || running}
            className="pqc-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            title="Export full benchmark telemetry in JSON"
          >
            <svg className="w-3.5 h-3.5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Export JSON</span>
          </button>
          <button
            onClick={handleExportCsv}
            disabled={!benchmarkData || running}
            className="pqc-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            title="Export tabulated benchmark figures in CSV"
          >
            <svg className="w-3.5 h-3.5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          <div className="font-semibold mb-0.5">Benchmark Error</div>
          <div>{error}</div>
        </div>
      )}

      {/* Benchmark Control Bar */}
      <div className="pqc-card p-5 space-y-4">
        <div className="text-xs font-semibold text-neutral-300 pb-1 flex items-center justify-between">
          <span>Benchmark Suite Configuration</span>
          {benchmarkData && (
            <span className="text-[11px] font-normal text-neutral-400">
              Last executed: {new Date(benchmarkData.timestamp).toLocaleTimeString()} ({benchmarkData.iterations} iterations)
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-1.5">
              Iterations per primitive
            </label>
            <select
              value={iterations}
              onChange={(e) => setIterations(Number(e.target.value))}
              disabled={running}
              className="pqc-input text-xs"
            >
              <option value={5} className="bg-[#111214]">5 iterations (Fast preview)</option>
              <option value={10} className="bg-[#111214]">10 iterations (Balanced evaluation)</option>
              <option value={20} className="bg-[#111214]">20 iterations (High statistical accuracy)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-1.5">
              Symmetric Payloads
            </label>
            <select
              value={selectedSizePreset}
              onChange={(e) => setSelectedSizePreset(e.target.value)}
              disabled={running}
              className="pqc-input text-xs"
            >
              <option value="quick" className="bg-[#111214]">1 KB payload</option>
              <option value="standard" className="bg-[#111214]">1 KB & 64 KB</option>
              <option value="heavy" className="bg-[#111214]">1 KB, 64 KB & 1 MB</option>
            </select>
          </div>

          <div className="flex items-center gap-4 py-2">
            <label className="flex items-center text-xs font-medium text-neutral-300 cursor-pointer">
              <input
                type="checkbox"
                checked={includePqc}
                onChange={(e) => setIncludePqc(e.target.checked)}
                disabled={running}
                className="h-4 w-4 rounded bg-white/[0.05] border-white/[0.2] text-emerald-500 accent-emerald-500 mr-2 cursor-pointer"
              />
              PQC (ML-KEM / ML-DSA)
            </label>
            <label className="flex items-center text-xs font-medium text-neutral-300 cursor-pointer">
              <input
                type="checkbox"
                checked={includeClassical}
                onChange={(e) => setIncludeClassical(e.target.checked)}
                disabled={running}
                className="h-4 w-4 rounded bg-white/[0.05] border-white/[0.2] text-emerald-500 accent-emerald-500 mr-2 cursor-pointer"
              />
              Classical (X25519 / Ed25519)
            </label>
          </div>

          <div>
            <button
              onClick={handleRunBenchmark}
              disabled={running || (!includePqc && !includeClassical)}
              className="pqc-btn-primary w-full py-2.5 text-xs font-semibold flex items-center justify-center gap-2"
            >
              {running ? (
                <>
                  <span className="pqc-dot-pulse"></span>
                  <span>Running Benchmarks...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 text-neutral-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>Run Benchmark Suite</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Environment Metadata & Host Warning Card */}
      {activeEnv && (
        <div className="pqc-card p-5 bg-[#0c0d0e] border border-white/[0.08] space-y-4">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 pb-1">
            <div>
              <div className="flex items-center gap-2">
                <span className="pqc-dot-pulse"></span>
                <span className="text-xs font-semibold text-emerald-400">
                  Execution Environment
                </span>
              </div>
              <h2 className="text-base font-semibold text-white mt-1">
                {activeEnv.cpu_model || 'Standard CPU'} ({activeEnv.cpu_cores || 'Multi'}-Core)
              </h2>
            </div>
            <div className="text-left md:text-right text-xs text-neutral-400 space-y-0.5">
              <div>OS: {activeEnv.os_name || activeEnv.os || 'Linux / Windows'} {activeEnv.os_version || ''} ({activeEnv.architecture || 'x86_64'})</div>
              <div>Memory: {((activeEnv.total_ram_gb ?? activeEnv.total_memory_gb) ?? 16.0).toFixed(1)} GB Physical RAM</div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="pqc-card p-3 bg-[#111214] border-white/[0.06]">
              <span className="text-neutral-400 text-[11px] block">PQC Cryptographic Engine</span>
              <span className="font-semibold text-emerald-300 mt-0.5 block truncate">{activeEnv.pqc_backend || 'liboqs-python'}</span>
            </div>
            <div className="pqc-card p-3 bg-[#111214] border-white/[0.06]">
              <span className="text-neutral-400 text-[11px] block">Python Runtime</span>
              <span className="font-semibold text-neutral-200 mt-0.5 block">{activeEnv.python_version || '3.11+'}</span>
            </div>
            <div className="pqc-card p-3 bg-[#111214] border-white/[0.06]">
              <span className="text-neutral-400 text-[11px] block">Cryptography Library</span>
              <span className="font-semibold text-neutral-200 mt-0.5 block">v{activeEnv.cryptography_version || '42.0.0'}</span>
            </div>
            <div className="pqc-card p-3 bg-[#111214] border-white/[0.06]">
              <span className="text-neutral-400 text-[11px] block">Statistical Metrics</span>
              <span className="font-semibold text-neutral-200 mt-0.5 block">p50, p90, p95, p99, Min, Max</span>
            </div>
          </div>

          {activeEnv.environment_notice && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-300 leading-relaxed">
              <span className="font-semibold text-emerald-200">Environment Dependency Notice: </span>
              {activeEnv.environment_notice}
            </div>
          )}
        </div>
      )}

      {/* Comparative Executive Summary Cards */}
      {benchmarkData && benchmarkData.summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Latency Ratio Card */}
          <div className="pqc-card p-5 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-neutral-400">Total Computation Time</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {(benchmarkData.summary.pqc_total_time_ms ?? 0).toFixed(2)} ms
                </span>
                <span className="text-[11px] text-neutral-400">PQC suite</span>
              </div>
              <div className="text-xs text-neutral-400 mt-1">
                Classical: <span className="font-semibold text-neutral-200">{(benchmarkData.summary.classical_total_time_ms ?? 0).toFixed(2)} ms</span>
              </div>
            </div>
            <div className="mt-4 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-400">Overhead Ratio:</span>
                <span className="pqc-badge pqc-badge-quantum">
                  {((benchmarkData.summary.time_overhead_ratio ?? benchmarkData.summary.time_ratio) ?? 1).toFixed(2)}x
                </span>
              </div>
            </div>
          </div>

          {/* Key Size Overhead Card */}
          <div className="pqc-card p-5 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-neutral-400">Public Key Footprint</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-cyan-400">1,184 Bytes</span>
                <span className="text-[11px] text-neutral-400">ML-KEM-768</span>
              </div>
              <div className="text-xs text-neutral-400 mt-1">
                X25519: <span className="font-semibold text-neutral-200">32 Bytes</span> (Curve25519)
              </div>
            </div>
            <div className="mt-4 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-400">Key Overhead:</span>
                <span className="pqc-badge pqc-badge-cyan">
                  {(benchmarkData.summary.key_size_overhead_ratio ?? 37).toFixed(1)}x
                </span>
              </div>
            </div>
          </div>

          {/* Signature Size Overhead Card */}
          <div className="pqc-card p-5 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-neutral-400">Signature Footprint</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-emerald-400">3,309 Bytes</span>
                <span className="text-[11px] text-neutral-400">ML-DSA-65</span>
              </div>
              <div className="text-xs text-neutral-400 mt-1">
                Ed25519: <span className="font-semibold text-neutral-200">64 Bytes</span> (Edwards-curve)
              </div>
            </div>
            <div className="mt-4 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-400">Signature Overhead:</span>
                <span className="pqc-badge pqc-badge-quantum">
                  {(benchmarkData.summary.signature_size_overhead_ratio ?? 51.7).toFixed(1)}x
                </span>
              </div>
            </div>
          </div>

          {/* Framing Overhead Card */}
          <div className="pqc-card p-5 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-neutral-400">Ciphertext / Framing</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-emerald-400">1,088 Bytes</span>
                <span className="text-[11px] text-neutral-400">KEM Encapsulation</span>
              </div>
              <div className="text-xs text-neutral-400 mt-1">
                AES-GCM Framing: <span className="font-semibold text-neutral-200">28 Bytes</span> (12B IV + 16B Tag)
              </div>
            </div>
            <div className="mt-4 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-400">Shared Secret:</span>
                <span className="pqc-badge pqc-badge-quantum">
                  32 Bytes (256-bit)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Visual Comparative Bar Charts */}
      {benchmarkData && (
        <div className="pqc-card p-6 space-y-6">
          <h2 className="text-xs font-semibold text-neutral-300 pb-1">
            Post-Quantum vs. Classical Comparative Analysis
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Visual 1: Key Exchange Comparison */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-neutral-300">
                Key Establishment (ML-KEM-768 vs X25519)
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-medium text-neutral-300 mb-1.5">
                    <span>ML-KEM-768 (Encapsulation + Decapsulation)</span>
                    <span className="font-bold text-cyan-400">1,088 B Ciphertext</span>
                  </div>
                  <div className="w-full bg-[#0c0d0e] rounded-full h-2.5 overflow-hidden border border-white/[0.06]">
                    <div className="bg-cyan-500 h-full rounded-full" style={{ width: '92%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-neutral-300 mb-1.5">
                    <span>X25519 (Diffie-Hellman Key Agreement)</span>
                    <span className="font-bold text-amber-400">32 B Public Key</span>
                  </div>
                  <div className="w-full bg-[#0c0d0e] rounded-full h-2.5 overflow-hidden border border-white/[0.06]">
                    <div className="bg-amber-500 h-full rounded-full" style={{ width: '8%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual 2: Signature Comparison */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-neutral-300">
                Digital Signatures (ML-DSA-65 vs Ed25519)
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-medium text-neutral-300 mb-1.5">
                    <span>ML-DSA-65 Signature Size</span>
                    <span className="font-bold text-emerald-400">3,309 Bytes</span>
                  </div>
                  <div className="w-full bg-[#0c0d0e] rounded-full h-2.5 overflow-hidden border border-white/[0.06]">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '98%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-neutral-300 mb-1.5">
                    <span>Ed25519 Signature Size</span>
                    <span className="font-bold text-amber-400">64 Bytes</span>
                  </div>
                  <div className="w-full bg-[#0c0d0e] rounded-full h-2.5 overflow-hidden border border-white/[0.06]">
                    <div className="bg-amber-500 h-full rounded-full" style={{ width: '3%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabular Statistical Breakdown */}
      <div className="pqc-card overflow-hidden">
        {/* Category Filter Tabs */}
        <div className="bg-[#0c0d0e]/80 px-5 py-3 flex flex-wrap gap-2">
          {[
            { id: 'all', label: 'All Operations' },
            { id: 'key_generation', label: 'Key Generation' },
            { id: 'key_establishment', label: 'Key Establishment (KEM / ECDH)' },
            { id: 'signatures', label: 'Digital Signatures' },
            { id: 'symmetric_encryption', label: 'Symmetric Encryption (AES-GCM)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeCategory === tab.id
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                  : 'text-neutral-400 hover:text-white hover:bg-white/[0.03]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          {loading && !benchmarkData ? (
            <div className="p-8 text-center text-xs text-neutral-400 space-y-2">
              <span className="pqc-dot-pulse inline-block"></span>
              <p>Measuring cryptographic performance across algorithms...</p>
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="p-8 text-center text-xs text-neutral-400">
              No benchmark results in this category. Click "Run Benchmark Suite" above.
            </div>
          ) : (
            <table className="pqc-table">
              <thead>
                <tr>
                  <th>Operation</th>
                  <th>Algorithm</th>
                  <th>Mode</th>
                  <th className="text-right">Median (p50)</th>
                  <th className="text-right">p90</th>
                  <th className="text-right">p95</th>
                  <th className="text-right">Min / Max</th>
                  <th className="text-right">Key / Output Size</th>
                  <th className="text-right">Overhead / Throughput</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((item: BenchmarkItem, idx: number) => {
                  const isPqc = item.mode === 'pqc'
                  const isClassical = item.mode === 'classical'

                  // Compute size text
                  let sizeText = '-'
                  if (item.sizes.public_key_bytes) {
                    sizeText = `PK: ${item.sizes.public_key_bytes} B`
                  } else if (item.sizes.ciphertext_bytes) {
                    sizeText = `CT: ${item.sizes.ciphertext_bytes} B`
                  } else if (item.sizes.signature_bytes) {
                    sizeText = `Sig: ${item.sizes.signature_bytes} B`
                  }

                  // Compute secondary metric
                  let secondaryText = '-'
                  if (item.throughput_mb_s) {
                    secondaryText = `${item.throughput_mb_s.toFixed(1)} MB/s`
                  } else if (item.sizes.overhead_bytes !== null && item.sizes.overhead_bytes !== undefined) {
                    secondaryText = `+${item.sizes.overhead_bytes} B`
                  } else if (item.sizes.shared_secret_bytes) {
                    secondaryText = `SS: ${item.sizes.shared_secret_bytes} B`
                  }

                  return (
                    <tr key={`${item.operation}-${item.algorithm}-${idx}`}>
                      <td className="font-sans font-medium text-white">
                        {item.operation}
                        {item.payload_size_bytes && (
                          <span className="block text-[10px] text-neutral-400">
                            Payload: {(item.payload_size_bytes / 1024).toFixed(0)} KB
                          </span>
                        )}
                      </td>
                      <td className="font-sans font-semibold text-neutral-200">
                        {item.algorithm}
                      </td>
                      <td className="font-sans">
                        <span className={`pqc-badge ${isPqc ? 'pqc-badge-quantum' : isClassical ? 'pqc-badge-warning' : 'pqc-badge-cyan'} text-[10px] py-0 px-2`}>
                          {item.mode.toUpperCase()}
                        </span>
                      </td>
                      <td className="text-right font-bold text-white tabular-nums">
                        {(item.timing?.median_ms ?? 0).toFixed(3)} ms
                      </td>
                      <td className="text-right text-neutral-300 tabular-nums">
                        {(item.timing?.p90_ms ?? 0).toFixed(3)} ms
                      </td>
                      <td className="text-right text-neutral-300 tabular-nums">
                        {(item.timing?.p95_ms ?? 0).toFixed(3)} ms
                      </td>
                      <td className="text-right text-neutral-400 text-[11px] tabular-nums">
                        {(item.timing?.min_ms ?? 0).toFixed(3)} / {(item.timing?.max_ms ?? 0).toFixed(3)} ms
                      </td>
                      <td className="text-right font-sans text-neutral-300">
                        {sizeText}
                      </td>
                      <td className="text-right font-sans font-medium text-emerald-400">
                        {secondaryText}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
