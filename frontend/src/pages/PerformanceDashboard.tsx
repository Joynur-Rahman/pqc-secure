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
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Performance Measurement & Evaluation</h1>
          <p className="text-sm text-gray-600 mt-1">
            Empirical benchmarking of Post-Quantum Cryptography (ML-KEM-768, ML-DSA-65) vs. Classical (X25519, Ed25519) and AES-256-GCM.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportJson}
            disabled={!benchmarkData || running}
            className="px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 transition"
            title="Export full benchmark telemetry in JSON"
          >
            📥 Export JSON
          </button>
          <button
            onClick={handleExportCsv}
            disabled={!benchmarkData || running}
            className="px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 transition"
            title="Export tabulated benchmark figures in CSV"
          >
            📊 Export CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
          <div className="font-semibold">Benchmark Error</div>
          <div>{error}</div>
        </div>
      )}

      {/* Benchmark Control Bar */}
      <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
        <div className="text-sm font-semibold text-gray-900 border-b border-gray-100 pb-2 flex items-center justify-between">
          <span>Benchmark Suite Configuration</span>
          {benchmarkData && (
            <span className="text-xs font-normal text-gray-500">
              Last executed: {new Date(benchmarkData.timestamp).toLocaleTimeString()} ({benchmarkData.iterations} iterations)
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Iterations per primitive
            </label>
            <select
              value={iterations}
              onChange={(e) => setIterations(Number(e.target.value))}
              disabled={running}
              className="w-full text-sm border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 py-1.5"
            >
              <option value={5}>5 iterations (Fast preview)</option>
              <option value={10}>10 iterations (Balanced evaluation)</option>
              <option value={20}>20 iterations (High statistical accuracy)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Symmetric Payloads
            </label>
            <select
              value={selectedSizePreset}
              onChange={(e) => setSelectedSizePreset(e.target.value)}
              disabled={running}
              className="w-full text-sm border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 py-1.5"
            >
              <option value="quick">1 KB payload</option>
              <option value="standard">1 KB & 64 KB</option>
              <option value="heavy">1 KB, 64 KB & 1 MB</option>
            </select>
          </div>

          <div className="flex items-center gap-4 py-2">
            <label className="flex items-center text-xs font-medium text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={includePqc}
                onChange={(e) => setIncludePqc(e.target.checked)}
                disabled={running}
                className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 mr-2"
              />
              PQC (ML-KEM / ML-DSA)
            </label>
            <label className="flex items-center text-xs font-medium text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={includeClassical}
                onChange={(e) => setIncludeClassical(e.target.checked)}
                disabled={running}
                className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 mr-2"
              />
              Classical (X25519 / Ed25519)
            </label>
          </div>

          <div>
            <button
              onClick={handleRunBenchmark}
              disabled={running || (!includePqc && !includeClassical)}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md shadow-sm transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {running ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>Running Benchmarks...</span>
                </>
              ) : (
                <>
                  <span>⚡ Run Benchmark Suite</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Environment Metadata & Host Warning Card */}
      {activeEnv && (
        <div className="bg-gradient-to-r from-gray-900 to-gray-800 text-white rounded-lg p-5 shadow">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 border-b border-gray-700 pb-4 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                  Execution Environment
                </span>
              </div>
              <h2 className="text-lg font-bold text-white mt-1">
                {activeEnv.cpu_model} ({activeEnv.cpu_cores} Cores)
              </h2>
            </div>
            <div className="text-right text-xs text-gray-300">
              <div>OS: {activeEnv.os_name} {activeEnv.os_version} ({activeEnv.architecture})</div>
              <div>Memory: {activeEnv.total_ram_gb.toFixed(1)} GB Physical RAM</div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="bg-gray-800/80 p-2.5 rounded border border-gray-700">
              <span className="text-gray-400 block">PQC Cryptographic Engine</span>
              <span className="font-semibold text-emerald-300">{activeEnv.pqc_backend}</span>
            </div>
            <div className="bg-gray-800/80 p-2.5 rounded border border-gray-700">
              <span className="text-gray-400 block">Python Runtime</span>
              <span className="font-semibold text-gray-200">{activeEnv.python_version}</span>
            </div>
            <div className="bg-gray-800/80 p-2.5 rounded border border-gray-700">
              <span className="text-gray-400 block">Cryptography Library</span>
              <span className="font-semibold text-gray-200">v{activeEnv.cryptography_version}</span>
            </div>
            <div className="bg-gray-800/80 p-2.5 rounded border border-gray-700">
              <span className="text-gray-400 block">Statistical Metrics</span>
              <span className="font-semibold text-gray-200">p50, p90, p95, p99, Min, Max</span>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-950/60 border border-blue-800/80 rounded text-xs text-blue-200">
            <span className="font-semibold text-blue-100">Environment Dependency Notice: </span>
            {activeEnv.environment_notice}
          </div>
        </div>
      )}

      {/* Comparative Executive Summary Cards */}
      {benchmarkData && benchmarkData.summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Latency Ratio Card */}
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Computation Time</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-gray-900">
                  {benchmarkData.summary.pqc_total_time_ms.toFixed(2)} ms
                </span>
                <span className="text-xs text-gray-500">PQC suite</span>
              </div>
              <div className="text-xs text-gray-600 mt-1">
                Classical: <span className="font-semibold">{benchmarkData.summary.classical_total_time_ms.toFixed(2)} ms</span>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Timing Overhead Ratio:</span>
                <span className="font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  {benchmarkData.summary.time_ratio.toFixed(2)}x
                </span>
              </div>
            </div>
          </div>

          {/* Key Size Overhead Card */}
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Public Key Footprint</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-purple-700">1,184 Bytes</span>
                <span className="text-xs text-gray-500">ML-KEM-768</span>
              </div>
              <div className="text-xs text-gray-600 mt-1">
                X25519: <span className="font-semibold">32 Bytes</span> (Curve25519)
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">KEM Key Size Ratio:</span>
                <span className="font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                  {benchmarkData.summary.key_size_overhead_ratio.toFixed(1)}x
                </span>
              </div>
            </div>
          </div>

          {/* Signature Size Overhead Card */}
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Signature Footprint</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-indigo-700">3,309 Bytes</span>
                <span className="text-xs text-gray-500">ML-DSA-65</span>
              </div>
              <div className="text-xs text-gray-600 mt-1">
                Ed25519: <span className="font-semibold">64 Bytes</span> (Edwards-curve)
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Signature Size Ratio:</span>
                <span className="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                  {benchmarkData.summary.signature_size_overhead_ratio.toFixed(1)}x
                </span>
              </div>
            </div>
          </div>

          {/* Framing Overhead Card */}
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex flex-col justify-between">
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Ciphertext / Framing</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-emerald-700">1,088 Bytes</span>
                <span className="text-xs text-gray-500">KEM Encapsulation</span>
              </div>
              <div className="text-xs text-gray-600 mt-1">
                AES-GCM Framing: <span className="font-semibold">28 Bytes</span> (12B IV + 16B Tag)
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Shared Secret:</span>
                <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  32 Bytes (256-bit)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Visual Comparative Bar Charts */}
      {benchmarkData && (
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm space-y-6">
          <h2 className="text-base font-bold text-gray-900 border-b border-gray-100 pb-3">
            Post-Quantum vs. Classical Comparative Analysis
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Visual 1: Key Exchange Comparison */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Key Establishment (ML-KEM-768 vs X25519)
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                    <span>ML-KEM-768 (Encapsulation + Decapsulation)</span>
                    <span className="font-bold text-purple-600">1,088 B Ciphertext</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div className="bg-purple-600 h-3 rounded-full" style={{ width: '92%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                    <span>X25519 (Diffie-Hellman Key Agreement)</span>
                    <span className="font-bold text-gray-600">32 B Public Key</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div className="bg-blue-500 h-3 rounded-full" style={{ width: '8%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual 2: Signature Comparison */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Digital Signatures (ML-DSA-65 vs Ed25519)
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                    <span>ML-DSA-65 Signature Size</span>
                    <span className="font-bold text-indigo-600">3,309 Bytes</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div className="bg-indigo-600 h-3 rounded-full" style={{ width: '98%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                    <span>Ed25519 Signature Size</span>
                    <span className="font-bold text-gray-600">64 Bytes</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div className="bg-emerald-500 h-3 rounded-full" style={{ width: '3%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabular Statistical Breakdown */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        {/* Category Filter Tabs */}
        <div className="border-b border-gray-200 bg-gray-50 px-6 py-3 flex flex-wrap gap-2">
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
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                activeCategory === tab.id
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          {loading && !benchmarkData ? (
            <div className="p-8 text-center text-sm text-gray-500">
              Measuring cryptographic performance across algorithms...
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500">
              No benchmark results in this category. Click "Run Benchmark Suite" above.
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
              <thead className="bg-gray-100 text-gray-700 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-4 py-3">Operation</th>
                  <th className="px-4 py-3">Algorithm</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3 text-right">Median (p50)</th>
                  <th className="px-4 py-3 text-right">p90</th>
                  <th className="px-4 py-3 text-right">p95</th>
                  <th className="px-4 py-3 text-right">Min / Max</th>
                  <th className="px-4 py-3 text-right">Key / Output Size</th>
                  <th className="px-4 py-3 text-right">Overhead / Throughput</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white font-mono">
                {filteredResults.map((item: BenchmarkItem, idx: number) => {
                  const modeBadgeClass =
                    item.mode === 'pqc'
                      ? 'bg-purple-100 text-purple-800 border-purple-200'
                      : item.mode === 'classical'
                      ? 'bg-blue-100 text-blue-800 border-blue-200'
                      : 'bg-emerald-100 text-emerald-800 border-emerald-200'

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
                    <tr key={`${item.operation}-${item.algorithm}-${idx}`} className="hover:bg-gray-50/80 transition">
                      <td className="px-4 py-3 font-sans font-medium text-gray-900">
                        {item.operation}
                        {item.payload_size_bytes && (
                          <span className="block text-[11px] text-gray-400 font-mono">
                            Payload: {(item.payload_size_bytes / 1024).toFixed(0)} KB
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-700 font-sans font-semibold">
                        {item.algorithm}
                      </td>
                      <td className="px-4 py-3 font-sans">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${modeBadgeClass}`}>
                          {item.mode.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-bold text-gray-900">
                        {item.timing.median_ms.toFixed(3)} ms
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {item.timing.p90_ms.toFixed(3)} ms
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {item.timing.p95_ms.toFixed(3)} ms
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500 text-[11px]">
                        {item.timing.min_ms.toFixed(3)} / {item.timing.max_ms.toFixed(3)} ms
                      </td>
                      <td className="px-4 py-3 text-right font-sans text-gray-700">
                        {sizeText}
                      </td>
                      <td className="px-4 py-3 text-right font-sans font-medium text-gray-800">
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
