import Link from 'next/link';
import { MetricCard } from '@/components/MetricCard';
import { getCompanyProfile } from '@/lib/api';

export default async function CompanyPage({ params }: { params: Promise<{ stock_code: string }> }) {
  const { stock_code } = await params;
  let data = null;
  let error: string | null = null;

  try {
    data = await getCompanyProfile(stock_code);
  } catch (e: any) {
    error = e.message;
  }

  if (error || !data) {
    return (
      <section className="panel">
        <h2>Company Profile</h2>
        <p>{error || 'Company profile is not available.'}</p>
      </section>
    );
  }

  const signal = data.signal;
  const topicBreakdown: Array<[string, number]> = signal
    ? [
        ['Environmental', signal.e_count],
        ['Social', signal.s_count],
        ['Governance', signal.g_count],
        ['Mixed', signal.mixed_count],
      ]
    : [];
  const dominantTopic = signal
    ? topicBreakdown.slice().sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'
    : 'N/A';
  const totalTopicCount = topicBreakdown.reduce((sum, [, count]) => sum + count, 0);

  return (
    <section className="stack-xl">
      <section className="hero-panel compact">
        <div className="hero-copy">
          <span className="eyebrow">Company profile</span>
          <h2>
            {data.company.company_name} <span className="soft-inline">({data.company.stock_code})</span>
          </h2>
          <p className="hero-text">
            Use this page when you want a quick company snapshot before asking deeper questions in chat or adding the
            name into a comparison set.
          </p>
          <div className="hero-actions">
            <Link href={`/compare?codes=${data.company.stock_code}`} className="button-link secondary">Compare This Company</Link>
            <Link href={`/predictions?code=${data.company.stock_code}`} className="button-link secondary">Predict Rating</Link>
            <Link href={`/chat?codes=${data.company.stock_code}`} className="button-link primary">Ask in Chat</Link>
          </div>
        </div>
        <div className="hero-aside">
          <article className="mini-story">
            <p className="mini-story-label">Snapshot</p>
            <p>{data.company.industry || 'Unknown industry'}</p>
            <p>{data.company.esg_rating_raw || 'No ESG rating available'}</p>
          </article>
        </div>
      </section>

      <section className="dashboard-metrics">
        <MetricCard title="Industry" value={data.company.industry || 'Unknown'} subtitle="Sector context for this issuer" tone="accent" />
        <MetricCard title="ESG Rating" value={data.company.esg_rating_raw || 'N/A'} subtitle="From the structured ESG metadata set" />
        <MetricCard title="Disclosure Density" value={signal ? signal.esg_density : 'N/A'} subtitle="Share of ESG-tagged content in processed text" tone="warm" />
        <MetricCard title="Dominant Topic" value={dominantTopic} subtitle="Which ESG theme appears most often" />
      </section>

      <section className="insight-grid">
        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Topic balance</span>
              <h3>How this company’s ESG coverage is distributed</h3>
            </div>
          </div>

          {signal ? (
            <div className="bar-list">
              {topicBreakdown.map(([label, count]) => {
                const width = totalTopicCount ? `${(count / totalTopicCount) * 100}%` : '0%';
                const tone = label === 'Environmental' ? 'topic-e' : label === 'Social' ? 'topic-s' : label === 'Governance' ? 'topic-g' : 'topic-mixed';
                return (
                  <div key={label} className="bar-row">
                    <div className="bar-label">
                      <strong>{label}</strong>
                      <span>{count}</span>
                    </div>
                    <div className="bar-track">
                      <div className={`bar-fill ${tone}`} style={{ width }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-note">Signal metrics are not available for this company yet.</p>
          )}
        </article>

        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Research hooks</span>
              <h3>Keywords worth following up on</h3>
            </div>
          </div>

          <div className="chip-cloud">
            {(data.top_keywords || []).map((keyword) => (
              <span key={keyword} className="brand-chip">{keyword}</span>
            ))}
          </div>
        </article>
      </section>

      <section className="insight-grid">
        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Structured strengths</span>
              <h3>What this company already scores well on</h3>
            </div>
          </div>
          <div className="chip-cloud">
            {(data.strengths || []).length ? (
              data.strengths.map((item) => (
                <span key={item} className="brand-chip">{item}</span>
              ))
            ) : (
              <p className="empty-note">No structured strengths available.</p>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">Index presence</span>
              <h3>Where this company appears</h3>
            </div>
          </div>
          <div className="chip-cloud">
            {(data.index_membership || []).length ? (
              data.index_membership.map((item) => (
                <span key={item} className="brand-chip subtle">{item}</span>
              ))
            ) : (
              <p className="empty-note">No index membership captured.</p>
            )}
          </div>
        </article>
      </section>
    </section>
  );
}
