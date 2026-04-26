export function MetricCard({
  title,
  value,
  subtitle,
  tone = 'default',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  tone?: 'default' | 'accent' | 'warm';
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <p className="metric-title">{title}</p>
      <p className="metric-value">{value}</p>
      {subtitle ? <p className="metric-subtitle">{subtitle}</p> : null}
    </article>
  );
}
