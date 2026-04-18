import { getCompanyProfile } from '@/lib/api';

export default async function CompanyPage({ params }: { params: { stock_code: string } }) {
  let data: any = null;
  let error: string | null = null;

  try {
    data = await getCompanyProfile(params.stock_code);
  } catch (e: any) {
    error = e.message;
  }

  if (error) {
    return <section className="panel"><h2>Company Profile</h2><p>{error}</p></section>;
  }

  return (
    <section className="grid">
      <article className="panel" style={{ gridColumn: 'span 12' }}>
        <h2>{data.company.company_name} ({data.company.stock_code})</h2>
        <p>Industry: {data.company.industry || 'Unknown'} | ESG Rating: {data.company.esg_rating_raw || 'N/A'}</p>
      </article>

      <article className="panel" style={{ gridColumn: 'span 6' }}>
        <h3>Top Keywords</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(data.top_keywords || []).map((k: string) => (
            <span key={k} className="brand-chip">{k}</span>
          ))}
        </div>
      </article>

      <article className="panel" style={{ gridColumn: 'span 6' }}>
        <h3>Signals</h3>
        {data.signal ? (
          <ul>
            <li>E: {data.signal.e_count}</li>
            <li>S: {data.signal.s_count}</li>
            <li>G: {data.signal.g_count}</li>
            <li>Mixed: {data.signal.mixed_count}</li>
            <li>Density: {data.signal.esg_density}</li>
          </ul>
        ) : (
          <p>No computed signals yet.</p>
        )}
      </article>

      <article className="panel" style={{ gridColumn: 'span 12' }}>
        <h3>Strengths</h3>
        <p>{(data.strengths || []).join(', ') || 'N/A'}</p>
      </article>
    </section>
  );
}
