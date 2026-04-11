export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20">
      <h1 className="text-3xl font-bold">Select a market</h1>
      <div className="flex gap-6">
        <a
          href="/uk"
          className="bg-vodafone text-white px-10 py-6 rounded-xl text-xl font-semibold hover:opacity-90 transition"
        >
          UK
        </a>
        <a
          href="/de"
          className="bg-gray-800 text-white px-10 py-6 rounded-xl text-xl font-semibold hover:opacity-90 transition"
        >
          Germany
        </a>
      </div>
    </div>
  )
}
