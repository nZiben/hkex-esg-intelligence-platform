'use client';

import { useState } from 'react';
import { CitationList } from '@/components/CitationList';
import { askChat } from '@/lib/api';

export default function ChatPage() {
  const [question, setQuestion] = useState('Compare governance disclosures between 00001 and 00002.');
  const [stockCodes, setStockCodes] = useState('00001,00002');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const onAsk = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await askChat(
        question,
        stockCodes
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      );
      setResult(payload);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="grid">
      <article className="panel" style={{ gridColumn: 'span 12' }}>
        <h2>ESG Analyst Chat</h2>
        <p>Ask for company ESG insights. Answers are grounded in citation snippets from ingested reports.</p>
      </article>

      <article className="panel" style={{ gridColumn: 'span 5' }}>
        <label>Stock Codes (optional, comma separated)</label>
        <input value={stockCodes} onChange={(e) => setStockCodes(e.target.value)} />

        <label style={{ marginTop: 12, display: 'block' }}>Question</label>
        <textarea rows={8} value={question} onChange={(e) => setQuestion(e.target.value)} />

        <div style={{ marginTop: 12 }}>
          <button onClick={onAsk} disabled={loading}>{loading ? 'Thinking...' : 'Ask'}</button>
        </div>
        {error ? <p>{error}</p> : null}
      </article>

      <article className="panel" style={{ gridColumn: 'span 7' }}>
        <h3>Answer</h3>
        <p style={{ whiteSpace: 'pre-wrap' }}>{result?.answer || 'Submit a question to get a citation-grounded response.'}</p>
        {result ? (
          <p>
            Confidence: {result.confidence} | Latency: {result.latency_ms}ms
          </p>
        ) : null}
        <h4>Citations</h4>
        <CitationList citations={result?.citations || []} />
      </article>
    </section>
  );
}
