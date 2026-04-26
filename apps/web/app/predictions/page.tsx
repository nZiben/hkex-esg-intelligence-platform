'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { CompanyPicker } from '@/components/CompanyPicker';
import { MetricCard } from '@/components/MetricCard';
import {
  getCompanies,
  runPrediction,
  type CompanySummary,
  type PredictionRunResponse,
} from '@/lib/api';

export default function PredictionsPage() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [result, setResult] = useState<PredictionRunResponse | null>(null);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    getCompanies()
      .then((payload) => {
        if (mounted) {
          setCompanies(payload);
          const codeFromUrl = typeof window !== 'undefined'
            ? new URLSearchParams(window.location.search).get('code')
            : null;
          if (codeFromUrl && payload.some((company) => company.stock_code === codeFromUrl)) {
            setSelectedCodes([codeFromUrl]);
          }
        }
      })
      .catch((err: Error) => {
        if (mounted) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoadingCompanies(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const selectedCompany = useMemo(
    () => companies.find((company) => company.stock_code === selectedCodes[0]),
    [companies, selectedCodes],
  );

  const handleRunPrediction = async () => {
    const stockCode = selectedCodes[0];
    if (!stockCode) {
      setError('Choose one company before running a prediction.');
      return;
    }

    setRunning(true);
    setError(null);
    try {
      const payload = await runPrediction(stockCode);
      setResult(payload);
    } catch (err: any) {
      setError(err.message || 'Prediction failed.');
    } finally {
      setRunning(false);
    }
  };

  const runAt = result
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(result.run_at))
    : null;

  return (
    <section className="stack-xl">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">Model predictions</span>
          <h2>Run the trained ESG model separately from the research workflow.</h2>
          <p className="hero-text">
            Select a company, run the teammate-trained HKQAA predictor on its ingested reports, then use the result as a
            starting point for profile review, comparison, or citation-backed chat.
          </p>
        </div>
        <div className="hero-aside">
          <article className="mini-story">
            <p className="mini-story-label">Model source</p>
            <p>Fine-tuned retriever plus deep regression head trained from HKQAA ratings.</p>
            <p>First run may take longer while the model loads into the API process.</p>
          </article>
        </div>
      </section>

      <section className="insight-grid">
        <article className="panel">
          <CompanyPicker
            companies={companies}
            selectedCodes={selectedCodes}
            onChange={(codes) => {
              setSelectedCodes(codes.slice(-1));
              setResult(null);
            }}
            label="Prediction target"
            placeholder={loadingCompanies ? 'Loading companies' : 'Search a company to predict'}
            hint="Choose one company. The API will use all ingested report chunks for that stock code."
            maxSelect={1}
          />

          <div className="inline-actions">
            <button type="button" className="button-link primary" onClick={handleRunPrediction} disabled={running}>
              {running ? 'Running Prediction...' : 'Run Prediction'}
            </button>
            {selectedCompany ? (
              <Link href={`/company/${selectedCompany.stock_code}`} className="button-link secondary">
                Open Profile
              </Link>
            ) : null}
          </div>

          {error ? <p className="error-banner">{error}</p> : null}
        </article>

        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">How to read it</span>
              <h3>Prediction is a model signal, not a citation.</h3>
            </div>
          </div>
          <div className="ranked-list">
            <div className="ranked-row">
              <div>
                <strong>Rating</strong>
                <p>The letter grade mapped from the model&apos;s numeric ESG score.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Evidence volume</strong>
                <p>Chunk and document counts show how much ingested text fed the prediction.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Next step</strong>
                <p>Use profile or chat to inspect why the company may deserve that rating.</p>
              </div>
            </div>
          </div>
        </article>
      </section>

      {result ? (
        <>
          <section className="dashboard-metrics">
            <MetricCard title="Predicted Rating" value={result.predicted_esg_rating} subtitle={result.company_name} tone="accent" />
            <MetricCard title="Predicted Score" value={result.predicted_score.toFixed(1)} subtitle="Clipped to a 0-100 scale" />
            <MetricCard title="Confidence" value={`${Math.round(result.confidence * 100)}%`} subtitle="Based on available report evidence" tone="warm" />
            <MetricCard title="Text Used" value={result.num_chunks} subtitle={`${result.doc_count} documents included`} />
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <span className="eyebrow">Latest model run</span>
                <h3>
                  {result.company_name} <span className="soft-inline">({result.stock_code})</span>
                </h3>
              </div>
              <p className="section-copy">{runAt ? `Generated ${runAt}` : 'Generated just now'}</p>
            </div>

            <div className="leader-grid">
              <article className="leader-card">
                <p className="leader-code">Model</p>
                <h4>{result.model_version}</h4>
                <p>Retriever embeddings are averaged across report chunks before the regression head predicts score.</p>
              </article>
              <article className="leader-card">
                <p className="leader-code">Research path</p>
                <h4>Validate the signal</h4>
                <p>Open the profile for company-level context or ask chat for citation-backed supporting evidence.</p>
                <div className="leader-actions">
                  <Link href={`/company/${result.stock_code}`} className="text-link">Open Profile</Link>
                  <Link href={`/chat?codes=${result.stock_code}`} className="text-link">Ask in Chat</Link>
                </div>
              </article>
            </div>
          </section>
        </>
      ) : (
        <section className="panel empty-stage">
          <h3>Prediction results will appear here</h3>
          <p>Choose a company and run the model when you need a standalone ESG rating estimate.</p>
        </section>
      )}
    </section>
  );
}
