export default function Footer() {
  return (
    <footer data-ui="main-footer" className="bg-[#08090a] border-t border-white/[0.08] mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-6">
          <div>
            <h3 className="text-xs font-semibold text-neutral-300 mb-3">About</h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              PQC Secure is an educational prototype demonstrating post-quantum cryptography for secure file sharing.
            </p>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-neutral-300 mb-3">Technology</h3>
            <ul className="space-y-2 text-xs text-neutral-400">
              <li className="flex items-center space-x-2">
                <span className="pqc-badge pqc-badge-quantum text-[10px] py-0 px-1.5">NIST FIPS 203</span>
                <span>ML-KEM-768 for key establishment</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="pqc-badge pqc-badge-quantum text-[10px] py-0 px-1.5">NIST FIPS 204</span>
                <span>ML-DSA-65 for digital signatures</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="pqc-badge pqc-badge-cyan text-[10px] py-0 px-1.5">Authenticated</span>
                <span>AES-256-GCM for encryption</span>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-neutral-300 mb-3">Disclaimer</h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              This is not independently audited. For demonstration purposes only.
            </p>
          </div>
        </div>
        <div className="pt-4 flex flex-col sm:flex-row justify-between items-center text-xs text-neutral-400">
          <p>© {new Date().getFullYear()} PQC Secure. Educational prototype implementation.</p>
          <div className="flex items-center space-x-2 mt-2 sm:mt-0">
            <span className="pqc-dot-pulse"></span>
            <span className="text-[11px] text-emerald-400 font-medium">Quantum-Safe Channel Ready</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
