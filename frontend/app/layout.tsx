import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Device Price Comparison',
  description: 'Compare Vodafone device prices vs market — UK & Germany',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <header className="bg-vodafone text-white px-6 py-4 shadow">
          <div className="max-w-screen-xl mx-auto flex items-center gap-6">
            <span className="font-bold text-xl tracking-tight">Device Price Comparison</span>
            <nav className="flex gap-4 text-sm font-medium">
              <a href="/uk" className="hover:underline">UK</a>
              <a href="/de" className="hover:underline">Germany</a>
            </nav>
          </div>
        </header>
        <main className="max-w-screen-xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  )
}
