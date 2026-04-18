'use client';

import { useState } from 'react';
import Link from 'next/link';
import { compareCompanies } from '@/lib/api';

export default function ComparePage() {
  const [codes, setCodes] = useState('00001,00002');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onCompare = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await compareCompanies(
        codes
          .split(',')
          .map((x) => x.trim())
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
        <h2>Company Comparison</h2>
        <p>Compare disclosure density, topic dominance, and sentiment balance side by side.</p>
      </article>

      <article className="panel" style={{ gridColumn: 'span 4' }}>
        <label>Stock Codes</label>
        <input value={codes} onChange={(e) => setCodes(e.target.value)} />
        <div style={{ marginTop: 12 }}>
          <button onClick={onCompare} disabled={loading}>{loading ? 'Comparing...' : 'Compare'}</button>
        </div>
        {error ? <p>{error}</p> : null}
      </article>

      <article className="panel" style={{ gridColumn: 'span 8' }}>
        {result ? (
          <>
            <h3>Recommendation</h3>
            <p>{result.recommendation_summary}</p>
            <h3>Cards</h3>
            <ul>
              {result.companies.map((c: any) => (
                <li key={c.stock_code}>
                  <strong>{c.stock_code}</strong> - {c.company_name} | Rating: {c.esg_rating_raw || 'N/A'} |
                  Density: {c.esg_density ?? 'N/A'} | Dominant: {c.dominant_topic || 'N/A'} |
                  <Link href={`/company/${c.stock_code}`}> View Profile</Link>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p>Run a comparison to populate insights.</p>
        )}
      </article>
    </section>
  );
}
