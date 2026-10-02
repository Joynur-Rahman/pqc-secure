export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-4">About</h3>
            <p className="text-sm text-gray-600">
              PQC Secure is an educational prototype demonstrating post-quantum cryptography for secure file sharing.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Technology</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>ML-KEM-768 for key establishment</li>
              <li>ML-DSA-65 for digital signatures</li>
              <li>AES-256-GCM for encryption</li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Disclaimer</h3>
            <p className="text-sm text-gray-600">
              This is not independently audited. For demonstration purposes only.
            </p>
          </div>
        </div>
        <div className="border-t border-gray-200 pt-6">
          <p className="text-sm text-gray-500">
            © {new Date().getFullYear()} PQC Secure. Educational prototype implementation.
          </p>
        </div>
      </div>
    </footer>
  )
}
