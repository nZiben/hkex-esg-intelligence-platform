create extension if not exists vector;

create table if not exists companies (
  stock_code text primary key,
  company_name text not null,
  industry text,
  esg_rating_raw text,
  esg_rating_ordinal double precision,
  universe_ranking text,
  peer_ranking text,
  strengths jsonb,
  weaknesses jsonb,
  index_membership jsonb
);

create table if not exists documents (
  id bigserial primary key,
  stock_code text not null references companies(stock_code) on delete cascade,
  doc_type text not null,
  source_file text not null,
  report_year int,
  text_clean text not null,
  created_at timestamptz default now(),
  unique(stock_code, doc_type, source_file)
);

create table if not exists chunks (
  id bigserial primary key,
  document_id bigint not null references documents(id) on delete cascade,
  chunk_index int not null,
  text text not null,
  embedding vector(1536),
  page_no int,
  unique(document_id, chunk_index)
);

create table if not exists esg_signals (
  stock_code text primary key references companies(stock_code) on delete cascade,
  e_count int not null default 0,
  s_count int not null default 0,
  g_count int not null default 0,
  mixed_count int not null default 0,
  esg_density double precision not null default 0,
  sentiment_pos double precision not null default 0,
  sentiment_neu double precision not null default 1,
  sentiment_neg double precision not null default 0,
  updated_at timestamptz default now()
);

create table if not exists predictions (
  id bigserial primary key,
  stock_code text not null references companies(stock_code) on delete cascade,
  predicted_esg_rating text not null,
  confidence double precision not null,
  model_version text not null,
  run_at timestamptz default now()
);

create table if not exists chat_logs (
  id bigserial primary key,
  session_id text not null,
  question text not null,
  answer text not null,
  citations_json jsonb,
  confidence double precision,
  latency_ms int not null,
  created_at timestamptz default now()
);

create index if not exists idx_documents_stock_code on documents(stock_code);
create index if not exists idx_documents_doc_type on documents(doc_type);
create index if not exists idx_chunks_document_id on chunks(document_id);
create index if not exists idx_chat_logs_session on chat_logs(session_id);
