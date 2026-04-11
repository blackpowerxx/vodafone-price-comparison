export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-24">
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">Phone Price Comparison</h1>
        <p className="text-gray-500 text-lg">See how Vodafone stacks up against the competition</p>
      </div>
      <div className="flex gap-4">
        <a
          href="/uk"
          className="group flex flex-col items-center gap-3 bg-white border border-gray-200 hover:border-vodafone hover:shadow-md rounded-2xl px-12 py-8 transition-all"
        >
          <span className="text-4xl">🇬🇧</span>
          <span className="font-semibold text-gray-800 group-hover:text-vodafone transition-colors">United Kingdom</span>
        </a>
        <a
          href="/de"
          className="group flex flex-col items-center gap-3 bg-white border border-gray-200 hover:border-gray-800 hover:shadow-md rounded-2xl px-12 py-8 transition-all"
        >
          <span className="text-4xl">🇩🇪</span>
          <span className="font-semibold text-gray-800 transition-colors">Germany</span>
        </a>
      </div>
    </div>
  )
}
