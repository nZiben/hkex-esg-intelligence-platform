import Link from 'next/link';

const workflows = [
  {
    title: 'Ask with evidence',
    body: 'Use the chat workspace to ask about climate, governance, sentiment, or industry posture and get citation-backed answers.',
    href: '/chat',
    cta: 'Open Chat',
  },
  {
    title: 'Compare companies fast',
    body: 'Search by company name, not stock code, then build a side-by-side ESG view for shortlisting and benchmarking.',
    href: '/compare',
    cta: 'Open Compare',
  },
  {
    title: 'Scan portfolio signals',
    body: 'Start with the dashboard when you need a fast read on coverage, density, and disclosure patterns across the dataset.',
    href: '/dashboard',
    cta: 'Open Dashboard',
  },
];

export default function HomePage() {
  return (
    <section className="stack-xl">
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">ESG research assistant for HKEX companies</span>
          <h2>Turn long ESG disclosures into a workflow analysts can actually use.</h2>
          <p className="hero-text">
            This product is built for the real pain point in ESG research: too much report text, not enough usable
            signal. Instead of asking users to remember stock codes, it lets them search companies, inspect summaries,
            compare names, and chat against cited evidence.
          </p>
          <div className="hero-actions">
            <Link href="/chat" className="button-link primary">Start in Chat</Link>
            <Link href="/dashboard" className="button-link secondary">View Dashboard</Link>
          </div>
        </div>

        <div className="hero-aside">
          <article className="mini-story">
            <p className="mini-story-label">Why this is useful</p>
            <ul className="feature-list">
              <li>Reduces report-reading time by surfacing cited ESG evidence directly.</li>
              <li>Helps non-technical users work by company name instead of raw IDs.</li>
              <li>Supports both exploration and decision-making: chat, compare, then inspect profile details.</li>
            </ul>
          </article>
        </div>
      </section>

      <section className="workflow-grid">
        {workflows.map((workflow) => (
          <article key={workflow.title} className="workflow-card">
            <p className="workflow-kicker">Core workflow</p>
            <h3>{workflow.title}</h3>
            <p>{workflow.body}</p>
            <Link href={workflow.href} className="text-link">{workflow.cta}</Link>
          </article>
        ))}
      </section>

      <section className="decision-band">
        <div>
          <span className="eyebrow">Recommended usage path</span>
          <h3>Start broad, then narrow down.</h3>
        </div>
        <div className="step-strip">
          <article className="step-card">
            <strong>1</strong>
            <p>Use the dashboard to spot where disclosure coverage or density stands out.</p>
          </article>
          <article className="step-card">
            <strong>2</strong>
            <p>Compare shortlisted companies to see who looks stronger before deeper reading.</p>
          </article>
          <article className="step-card">
            <strong>3</strong>
            <p>Ask the chat for grounded explanations and follow-ups with citation support.</p>
          </article>
        </div>
      </section>
    </section>
  );
}
