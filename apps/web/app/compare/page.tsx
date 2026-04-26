'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { CompanyPicker } from '@/components/CompanyPicker';
import { compareCompanies, getCompanies, type CompanySummary, type CompareResponse } from '@/lib/api';

export default function ComparePage() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    getCompanies()
      .then((payload) => {
        if (mounted) {
          setCompanies(payload);
          const codesFromUrl = ((typeof window !== 'undefined'
            ? new URLSearchParams(window.location.search).get('codes')
            : '') || '')
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean)
            .slice(0, 4);

          if (codesFromUrl.length) {
            setSelectedCodes(codesFromUrl);
          } else if (payload.length >= 2) {
            setSelectedCodes([payload[0].stock_code, payload[1].stock_code]);
          }
        }
      })
      .catch((err: Error) => {
        if (mounted) {
          setError(err.message);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const runComparison = async () => {
    if (selectedCodes.length < 2) {
      setError('Choose at least two companies before comparing.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = await compareCompanies(selectedCodes);
      setResult(payload);
    } catch (err: any) {
      setError(err.message || 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="stack-xl">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">Comparison studio</span>
          <h2>Shortlist companies by evidence, not by memory.</h2>
          <p className="hero-text">
            Comparison should feel like building an analyst brief. Search names, line them up, then decide which one
            deserves deeper chat-based interrogation.
          </p>
        </div>
        <div className="hero-aside">
          <article className="mini-story">
            <p className="mini-story-label">Best for</p>
            <p>Board-level summaries, peer benchmarking, and narrowing down candidates before presentation.</p>
          </article>
        </div>
      </section>

      <section className="insight-grid">
        <article className="panel">
          <CompanyPicker
            companies={companies}
            selectedCodes={selectedCodes}
            onChange={setSelectedCodes}
            label="Comparison set"
            placeholder="Search companies to compare"
            hint="Pick two to four companies. This is much more usable than typing stock codes manually."
            maxSelect={4}
          />

          <div className="inline-actions">
            <button type="button" className="button-link primary" onClick={runComparison} disabled={loading}>
              {loading ? 'Comparing…' : 'Run Comparison'}
            </button>
            {error ? <p className="error-banner">{error}</p> : null}
          </div>
        </article>

        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">How to use it</span>
              <h3>Compare first, then ask why</h3>
            </div>
          </div>
          <div className="ranked-list">
            <div className="ranked-row">
              <div>
                <strong>Density</strong>
                <p>Useful for seeing who is talking about ESG more extensively.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Dominant topic</strong>
                <p>Shows whether a company leans environmental, social, or governance in disclosures.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Next step</strong>
                <p>Open any profile or move into chat to validate the recommendation with citations.</p>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="panel">
        {result ? (
          <>
            <div className="section-head">
              <div>
                <span className="eyebrow">Recommendation</span>
                <h3>What the current comparison suggests</h3>
              </div>
              <p className="section-copy">{result.recommendation_summary}</p>
            </div>

            <div className="leader-grid">
              {result.companies.map((company) => (
                <article key={company.stock_code} className="leader-card compare-card">
                  <p className="leader-code">{company.stock_code}</p>
                  <h4>{company.company_name}</h4>
                  <div className="compare-metrics">
                    <span className="rating-pill">{company.esg_rating_raw || 'No rating'}</span>
                    <span>Density {company.esg_density ?? 'N/A'}</span>
                    <span>Dominant {company.dominant_topic || 'N/A'}</span>
                    <span>Sentiment {company.sentiment_balance ?? 'N/A'}</span>
                  </div>
                  <div className="leader-actions">
                    <Link href={`/company/${company.stock_code}`} className="text-link">Open Profile</Link>
                    <Link href={`/predictions?code=${company.stock_code}`} className="text-link">Predict Rating</Link>
                    <Link href="/chat" className="text-link">Interrogate in Chat</Link>
                  </div>
                </article>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-stage">
            <h3>Comparison results will appear here</h3>
            <p>Pick companies by name, run the comparison, then use the result as a launch point for deeper analysis.</p>
          </div>
        )}
      </section>
    </section>
  );
}
