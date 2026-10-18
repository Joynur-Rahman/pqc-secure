import RegisterForm from '../components/RegisterForm'

export default function Register() {
  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        {/* Left Column: Platform Showcase */}
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="pqc-dot-pulse bg-emerald-400" />
            <span>Generate Your Quantum-Resistant Identity</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-tight">
              Create an Account Protected by Post-Quantum Cryptography
            </h1>
            <p className="text-sm sm:text-base text-neutral-400 leading-relaxed max-w-xl">
              Get an instant cryptographic key vault. Your account is enabled with NIST FIPS 203 ML-KEM-768 for secret key encapsulation and FIPS 204 ML-DSA-65 for tamper-proof digital signing.
            </p>
          </div>

          {/* Highlights */}
          <div className="space-y-3 pt-2">
            <div className="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 text-sm">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 2l-2 2m-1.5 1.5L14 9l-1.5-1.5L10 10l2 2-6 6H2v-4l6-6-1.5-1.5L9 5l1.5 1.5 2.5-2.5z"/>
                </svg>
              </span>
              <div>
                <h4 className="text-xs font-semibold text-white">Automated Keypair Provisioning</h4>
                <p className="text-[11px] text-neutral-400 mt-0.5">
                  Generate client-side post-quantum keypairs on demand or upload existing public keys.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 text-sm">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </span>
              <div>
                <h4 className="text-xs font-semibold text-white">Harvest-Now-Decrypt-Later Immune</h4>
                <p className="text-[11px] text-neutral-400 mt-0.5">
                  Protects your sensitive payload against state actors storing ciphertexts today for future quantum decryption.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 text-sm">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
              </span>
              <div>
                <h4 className="text-xs font-semibold text-white">Hybrid Post-Quantum Mode</h4>
                <p className="text-[11px] text-neutral-400 mt-0.5">
                  Dual encapsulation combining classical X25519 with post-quantum Kyber for maximum backwards compatibility.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Register Form */}
        <div className="lg:col-span-5 w-full">
          <RegisterForm />
        </div>
      </div>
    </div>
  )
}
