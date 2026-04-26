import Link from 'next/link';
import { MetricCard } from '@/components/MetricCard';
import { getDashboardOverview } from '@/lib/api';

export default async function DashboardPage() {
  let data = null;
  let error: string | null = null;

  try {
    data = await getDashboardOverview();
  } catch (e: any) {
    error = e.message;
  }

  if (error || !data) {
    return (
      <section className="panel">
        <h2>Dashboard</h2>
        <p>{error || 'Dashboard data is not available yet.'}</p>
      </section>
    );
  }

  const industryEntries = Object.entries(data.industry_distribution || {}).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const topicEntries = Object.entries(data.topic_totals || {});
  const topicTotal = topicEntries.reduce((sum, [, value]) => sum + value, 0);

  return (
    <section className="stack-xl">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">Portfolio dashboard</span>
          <h2>Read the dataset before you read the reports.</h2>
          <p className="hero-text">
            This view is for triage. Analysts can spot where disclosure volume is concentrated, which industries dominate
            the set, and which companies deserve a closer conversation in chat.
          </p>
        </div>
        <div className="hero-aside">
          <article className="mini-story">
            <p className="mini-story-label">Best next action</p>
            <p>Pick a top-density name below, then move into company profile or chat for a cited explanation.</p>
          </article>
        </div>
      </section>

      <section className="dashboard-metrics">
        <MetricCard title="Tracked Companies" value={data.company_count} subtitle="Available for search and comparison" tone="accent" />
        <MetricCard title="Average ESG Density" value={data.avg_esg_density} subtitle="Share of tagged ESG content across reports" />
        <MetricCard title="Governance Sentences" value={data.topic_totals?.G || 0} subtitle="Most visible disclosure theme right now" tone="warm" />
        <MetricCard title="Environmental Sentences" value={data.topic_totals?.E || 0} subtitle="Useful for climate and resource questions" />
      </section>

      <section className="insight-grid">
        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Topic mix</span>
              <h3>Where the disclosure volume sits</h3>
            </div>
            <p className="section-copy">A fast way to understand whether the dataset is dominated by governance, environment, or social signals.</p>
          </div>

          <div className="bar-list">
            {topicEntries.map(([label, value]) => {
              const width = topicTotal ? `${(value / topicTotal) * 100}%` : '0%';
              return (
                <div key={label} className="bar-row">
                  <div className="bar-label">
                    <strong>{label}</strong>
                    <span>{value}</span>
                  </div>
                  <div className="bar-track">
                    <div className={`bar-fill topic-${label.toLowerCase()}`} style={{ width }} />
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Industry concentration</span>
              <h3>Where most companies come from</h3>
            </div>
            <p className="section-copy">Helpful when you want to understand dataset bias before drawing ESG conclusions.</p>
          </div>

          <div className="ranked-list">
            {industryEntries.map(([industry, count]) => (
              <div key={industry} className="ranked-row">
                <div>
                  <strong>{industry}</strong>
                  <p>{count} companies represented</p>
                </div>
                <span>{Math.round((count / data.company_count) * 100)}%</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <span className="eyebrow">High-attention names</span>
            <h3>Top companies by ESG density</h3>
          </div>
          <p className="section-copy">These are strong candidates to inspect first, compare, or send into the chat workspace.</p>
        </div>

        <div className="leader-grid">
          {data.top_companies_by_density.map((company) => (
            <article key={company.stock_code} className="leader-card">
              <p className="leader-code">{company.stock_code}</p>
              <h4>{company.company_name}</h4>
              <p>{company.industry || 'Unknown industry'}</p>
              <div className="leader-actions">
                <span className="rating-pill">{company.esg_rating_raw || 'No rating'}</span>
                <Link href={`/company/${company.stock_code}`} className="text-link">Open Profile</Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
