import Layout from '../components/Layout'

export default function AboutPage() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto py-12 px-4">
        <h1 className="text-4xl font-bold text-gray-900 mb-6">About Cube Foundry</h1>

        <div className="bg-white rounded-lg shadow-md p-8 space-y-6 text-gray-700 leading-relaxed">
          <section>
            <h2 className="text-2xl font-semibold text-gray-800 mb-3">What is Cube Foundry?</h2>
            <p>
              Cube Foundry is a web app built for Magic: The Gathering cube enthusiasts. It gives
              cube owners a place to manage their cube, run draft events, collect feedback from
              players, and get AI-powered insights into how the cube is performing over time.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-800 mb-3">Features</h2>
            <ul className="list-disc list-inside space-y-2">
              <li>Create and manage your cube — upload your card list and keep it up to date</li>
              <li>Run casual or advanced draft events with friends</li>
              <li>Collect post-draft feedback from players, including card add/cut recommendations</li>
              <li>Track per-card win rates and format statistics over all your drafts</li>
              <li>Generate AI-written draft summaries and cube health reports</li>
              <li>Link your cube's CubeCobra page for easy reference</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-800 mb-3">Who made this?</h2>
            <p>
              Cube Foundry was designed and built by <strong>Ian Braverman</strong> — a Magic: The
              Gathering player and software developer who wanted better tools for running cube
              drafts with friends.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-gray-800 mb-3">Tech Stack</h2>
            <p>
              The backend is built with <strong>FastAPI</strong> and <strong>PostgreSQL</strong>,
              hosted on <strong>Google Cloud Run</strong>. The frontend is <strong>React</strong>{' '}
              with TypeScript and Tailwind CSS, deployed via <strong>Firebase Hosting</strong>.
              AI features are powered by <strong>Google Gemini</strong>.
            </p>
          </section>
        </div>
      </div>
    </Layout>
  )
}
