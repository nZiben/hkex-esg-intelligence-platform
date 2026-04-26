export function CitationList({ citations }: { citations: any[] }) {
  if (!citations?.length) return <p className="empty-note">No citations available.</p>;

  return (
    <div className="citation-list">
      {citations.map((c) => (
        <article key={c.citation_id} className="citation-card">
          <div className="citation-head">
            <strong>{c.citation_id}</strong>
            <span>{c.stock_code}</span>
            <span>{c.doc_type}</span>
          </div>
          <p>{c.snippet}</p>
          <small>
            {c.source_file}
            {c.page_no ? ` • page ${c.page_no}` : ''}
          </small>
        </article>
      ))}
    </div>
  );
}
