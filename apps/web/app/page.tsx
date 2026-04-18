import Link from 'next/link';

export default function HomePage() {
  return (
    <section className="panel">
      <h2>Project 7 Environmental, Social and Governance (ESG) Chatbot</h2>
      <p>
        This platform combines report ingestion, ESG analytics, and retrieval-grounded Q&A for business decision support.
      </p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <Link href="/dashboard"><button>Open Dashboard</button></Link>
        <Link href="/chat"><button>Start Chat</button></Link>
        <Link href="/compare"><button>Compare Companies</button></Link>
      </div>
    </section>
  );
}
