import { MetricCard } from '@/components/MetricCard';
import { getDashboardOverview } from '@/lib/api';

export default async function DashboardPage() {
  let data: any = null;
  let error: string | null = null;

  try {
    data = await getDashboardOverview();
  } catch (e: any) {
    error = e.message;
  }

  if (error) {
    return <section className="panel"><h2>Dashboard</h2><p>{error}</p></section>;
  }

  return (
    <section className="grid">
      <article className="panel" style={{ gridColumn: 'span 12' }}>
        <h2>ESG Dashboard Overview</h2>
        <p>Portfolio-level ESG signal distribution and disclosure trend snapshots.</p>
      </article>

      <article style={{ gridColumn: 'span 3' }}><MetricCard title="Companies" value={data.company_count} /></article>
      <article style={{ gridColumn: 'span 3' }}><MetricCard title="Avg ESG Density" value={data.avg_esg_density} /></article>
      <article style={{ gridColumn: 'span 3' }}><MetricCard title="Governance Sentences" value={data.topic_totals?.G || 0} /></article>
      <article style={{ gridColumn: 'span 3' }}><MetricCard title="Environmental Sentences" value={data.topic_totals?.E || 0} /></article>

      <article className="panel" style={{ gridColumn: 'span 6' }}>
        <h3>Industry Distribution</h3>
        <ul>
          {Object.entries(data.industry_distribution || {}).map(([k, v]: any) => (
            <li key={k}>{k}: {String(v)}</li>
          ))}
        </ul>
      </article>

      <article className="panel" style={{ gridColumn: 'span 6' }}>
        <h3>Top Companies by Density</h3>
        <ul>
          {(data.top_companies_by_density || []).map((c: any) => (
            <li key={c.stock_code}>{c.stock_code} - {c.company_name} ({c.esg_rating_raw || 'N/A'})</li>
          ))}
        </ul>
      </article>
    </section>
  );
}
