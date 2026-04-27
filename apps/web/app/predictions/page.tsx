'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { CompanyPicker } from '@/components/CompanyPicker';
import { MetricCard } from '@/components/MetricCard';
import {
  getCompanies,
  runPrediction,
  runPredictionInsights,
  type AuxiliaryPredictionKind,
  type AuxiliaryPredictionRunResponse,
  type CompanySummary,
  type PredictionRunResponse,
} from '@/lib/api';

const predictionModes: { kind: AuxiliaryPredictionKind; label: string }[] = [
  { kind: 'all', label: 'All Signals' },
  { kind: 'topics', label: 'Topics' },
  { kind: 'themes', label: 'Themes' },
  { kind: 'sentiment', label: 'Sentiment' },
];

const pillarLabels: Record<string, string> = {
  E: 'Environmental',
  S: 'Social',
  G: 'Governance',
};

function formatRunAt(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function PredictionsPage() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [result, setResult] = useState<PredictionRunResponse | null>(null);
  const [insightResult, setInsightResult] = useState<AuxiliaryPredictionRunResponse | null>(null);
  const [insightKind, setInsightKind] = useState<AuxiliaryPredictionKind>('all');
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [running, setRunning] = useState(false);
  const [runningInsights, setRunningInsights] = useState(false);
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

  const handleRunInsights = async () => {
    const stockCode = selectedCodes[0];
    if (!stockCode) {
      setError('Choose one company before running a prediction.');
      return;
    }

    setRunningInsights(true);
    setError(null);
    try {
      const payload = await runPredictionInsights(stockCode, insightKind);
      setInsightResult(payload);
    } catch (err: any) {
      setError(err.message || 'Signal prediction failed.');
    } finally {
      setRunningInsights(false);
    }
  };

  const runAt = result ? formatRunAt(result.run_at) : null;
  const insightRunAt = insightResult ? formatRunAt(insightResult.run_at) : null;

  return (
    <section className="stack-xl">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">Model predictions</span>
          <h2>Run ESG rating and signal models separately from research.</h2>
          <p className="hero-text">
            Select a company, then run the teammate-trained rating predictor or the new topic, theme, and ESG sentiment
            predictors on its ingested reports.
          </p>
        </div>
        <div className="hero-aside">
          <article className="mini-story">
            <p className="mini-story-label">Model source</p>
            <p>Fine-tuned retriever, deep regression head, trained topic classifier, theme anchors, and ESG sentiment anchors.</p>
            <p>First run may take longer while the API loads model artifacts.</p>
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
              setInsightResult(null);
            }}
            label="Prediction target"
            placeholder={loadingCompanies ? 'Loading companies' : 'Search a company to predict'}
            hint="Choose one company. The API will use all ingested report chunks for that stock code."
            maxSelect={1}
          />

          <div className="prediction-mode-block">
            <div className="field-head">
              <label className="field-label">Signal model</label>
              <p className="field-hint">Run one signal family or collect every signal in a single API call.</p>
            </div>
            <div className="segmented-control" role="tablist" aria-label="Signal model">
              {predictionModes.map((mode) => (
                <button
                  key={mode.kind}
                  type="button"
                  className={`segment-button ${insightKind === mode.kind ? 'active' : ''}`}
                  onClick={() => {
                    setInsightKind(mode.kind);
                    setInsightResult(null);
                  }}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>

          <div className="inline-actions">
            <button type="button" className="button-link primary" onClick={handleRunPrediction} disabled={running}>
              {running ? 'Running Rating...' : 'Run Rating'}
            </button>
            <button
              type="button"
              className="button-link secondary"
              onClick={handleRunInsights}
              disabled={runningInsights}
            >
              {runningInsights ? 'Running Signals...' : 'Run Signals'}
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
              <h3>Each model gives a different view of the same report text.</h3>
            </div>
          </div>
          <div className="ranked-list">
            <div className="ranked-row">
              <div>
                <strong>Rating</strong>
                <p>The regression model maps report embeddings to a numeric ESG score and letter grade.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Topics</strong>
                <p>The trained classifier estimates the ISO 26000 topic families present in the report.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Themes</strong>
                <p>The detector ranks concrete ESG themes by chunk-level similarity against anchor descriptions.</p>
              </div>
            </div>
            <div className="ranked-row">
              <div>
                <strong>Sentiment</strong>
                <p>The E, S, and G pillars are compared with positive and negative benchmark anchors.</p>
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
                <span className="eyebrow">Latest rating run</span>
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
      ) : null}

      {insightResult ? (
        <section className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Latest signal run</span>
              <h3>
                {insightResult.company_name} <span className="soft-inline">({insightResult.stock_code})</span>
              </h3>
            </div>
            <p className="section-copy">
              {insightRunAt ? `Generated ${insightRunAt}` : 'Generated just now'} from {insightResult.num_chunks} chunks.
            </p>
          </div>

          <div className="prediction-results">
            {insightResult.topics.length ? (
              <article className="prediction-result-block">
                <div className="section-head compact-head">
                  <div>
                    <span className="eyebrow">Topic classifier</span>
                    <h3>Topic probabilities</h3>
                  </div>
                  <p className="section-copy">{insightResult.model_version}</p>
                </div>
                <div className="bar-list">
                  {insightResult.topics.map((topic) => (
                    <div className="bar-row" key={topic.label}>
                      <div className="bar-label">
                        <strong>{topic.label}</strong>
                        <span>{formatPercent(topic.probability)}</span>
                      </div>
                      <div className="bar-track">
                        <div className="bar-fill topic-g" style={{ width: formatPercent(topic.probability) }} />
                      </div>
                      <p className="empty-note">{topic.predicted ? 'Selected by threshold' : 'Below threshold'}</p>
                    </div>
                  ))}
                </div>
              </article>
            ) : null}

            {insightResult.themes.length ? (
              <article className="prediction-result-block">
                <div className="section-head compact-head">
                  <div>
                    <span className="eyebrow">Theme detector</span>
                    <h3>Top ESG themes</h3>
                  </div>
                  <p className="section-copy">{insightResult.doc_count} documents included</p>
                </div>
                <div className="bar-list">
                  {insightResult.themes.map((theme) => (
                    <div className="bar-row" key={theme.theme}>
                      <div className="bar-label">
                        <strong>{theme.theme}</strong>
                        <span>{theme.mentions} chunks</span>
                      </div>
                      <div className="bar-track">
                        <div className="bar-fill topic-e" style={{ width: formatPercent(theme.share) }} />
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ) : null}

            {insightResult.sentiment.length ? (
              <article className="prediction-result-block">
                <div className="section-head compact-head">
                  <div>
                    <span className="eyebrow">ESG sentiment</span>
                    <h3>Pillar stance</h3>
                  </div>
                </div>
                <div className="leader-grid">
                  {insightResult.sentiment.map((item) => (
                    <article className={`leader-card sentiment-card ${item.sentiment}`} key={item.pillar}>
                      <p className="leader-code">{pillarLabels[item.pillar] || item.pillar}</p>
                      <h4>{titleCase(item.sentiment)}</h4>
                      <p>
                        Positive {item.positive_similarity.toFixed(2)} vs negative {item.negative_similarity.toFixed(2)}
                      </p>
                      <span className="sentiment-margin">Margin {item.margin.toFixed(2)}</span>
                    </article>
                  ))}
                </div>
              </article>
            ) : null}
          </div>
        </section>
      ) : null}

      {!result && !insightResult ? (
        <section className="panel empty-stage">
          <h3>Prediction results will appear here</h3>
          <p>Choose a company, then run the rating model or one of the signal models.</p>
        </section>
      ) : null}
    </section>
  );
}
