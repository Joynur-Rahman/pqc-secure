import LoginForm from '../components/LoginForm'

export default function Login() {
  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        {/* Left Column: Platform Showcase */}
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="pqc-dot-pulse" />
            <span>FIPS 203 & FIPS 204 Standardized Cryptography</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-tight">
              Post-Quantum Cryptography for Secure File Sharing
            </h1>
            <p className="text-sm sm:text-base text-neutral-400 leading-relaxed max-w-xl">
              Neutralize Harvest-Now-Decrypt-Later (HNDL) attacks. PQC-Secure couples lattice-based ML-KEM-768 key encapsulation with ML-DSA-65 signatures and authenticated AES-256-GCM envelope encryption.
            </p>
          </div>

          {/* Feature Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <svg className="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                <span>ML-KEM-768</span>
              </div>
              <p className="text-[11px] text-neutral-400 mt-1 leading-normal">
                NIST FIPS 203 standardized module lattice key encapsulation mechanism.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <svg className="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 19l7-7 3 3-7 7-3-3z"/>
                  <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/>
                </svg>
                <span>ML-DSA-65</span>
              </div>
              <p className="text-[11px] text-neutral-400 mt-1 leading-normal">
                NIST FIPS 204 post-quantum digital signature authentication.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <svg className="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <span>Envelope Encryption</span>
              </div>
              <p className="text-[11px] text-neutral-400 mt-1 leading-normal">
                AES-256-GCM payload with multi-recipient hybrid headers.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <svg className="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <span>Hardware Telemetry</span>
              </div>
              <p className="text-[11px] text-neutral-400 mt-1 leading-normal">
                Hardware-accelerated liboqs with real-time empirical benchmarking.
              </p>
            </div>
          </div>

          {/* Security posture badges */}
          <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-neutral-400">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Post-Quantum Active</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-neutral-400" />
              <span>Hybrid Fallback Ready</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Zero-Knowledge Server</span>
            </div>
          </div>
        </div>

        {/* Right Column: Form */}
        <div className="lg:col-span-5 w-full">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}

