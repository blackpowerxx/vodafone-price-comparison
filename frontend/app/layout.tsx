import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Phone Price Comparison — UK & Germany',
  description: 'Compare Vodafone device prices vs EE, Three, Amazon and more',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body className="bg-gray-50 text-gray-900 min-h-screen antialiased">
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-vodafone flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white" aria-hidden="true">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
                </svg>
              </span>
              <span className="font-semibold text-gray-900 text-sm tracking-tight">Phone Price Comparison</span>
            </div>
            <nav className="flex gap-1">
              <a href="/uk" className="px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors">🇬🇧 UK</a>
              <a href="/de" className="px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors">🇩🇪 Germany</a>
            </nav>
          </div>
        </header>
        <main className="max-w-screen-2xl mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
