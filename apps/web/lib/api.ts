const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export type CompanySummary = {
  stock_code: string;
  company_name: string;
  industry: string | null;
  esg_rating_raw: string | null;
  esg_rating_ordinal: number | null;
};

export type Citation = {
  citation_id: string;
  stock_code: string;
  company_name?: string | null;
  doc_type: string;
  source_file: string;
  page_no?: number | null;
  snippet: string;
};

export type ChatQueryResponse = {
  answer: string;
  citations: Citation[];
  confidence: number;
  latency_ms: number;
  follow_up_questions: string[];
};

export type DashboardOverview = {
  company_count: number;
  industry_distribution: Record<string, number>;
  avg_esg_density: number;
  topic_totals: Record<string, number>;
  sentiment_totals: Record<string, number>;
  top_companies_by_density: CompanySummary[];
};

export type CompanyProfile = {
  company: CompanySummary;
  strengths: string[];
  weaknesses: string[];
  index_membership: string[];
  top_keywords: string[];
  signal?: {
    stock_code: string;
    e_count: number;
    s_count: number;
    g_count: number;
    mixed_count: number;
    esg_density: number;
    sentiment_pos: number;
    sentiment_neu: number;
    sentiment_neg: number;
  } | null;
  latest_prediction?: {
    predicted_esg_rating: string;
    confidence: number;
    model_version: string;
    run_at: string;
  } | null;
};

export type PredictionRunResponse = {
  stock_code: string;
  company_name: string;
  predicted_esg_rating: string;
  predicted_score: number;
  confidence: number;
  model_version: string;
  num_chunks: number;
  doc_count: number;
  run_at: string;
};

export type CompareCompanyCard = {
  stock_code: string;
  company_name: string;
  esg_rating_raw: string | null;
  esg_density: number | null;
  dominant_topic: string | null;
  sentiment_balance: number | null;
};

export type CompareResponse = {
  companies: CompareCompanyCard[];
  recommendation_summary: string;
};

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

export async function getCompanies(limit = 160) {
  return http<CompanySummary[]>(`/api/v1/companies?limit=${limit}&offset=0`);
}

export async function getDashboardOverview() {
  return http<DashboardOverview>('/api/v1/dashboard/overview');
}

export async function getCompanyProfile(stockCode: string) {
  return http<CompanyProfile>(`/api/v1/companies/${stockCode}/profile`);
}

export async function compareCompanies(codes: string[]) {
  return http<CompareResponse>(`/api/v1/compare?codes=${codes.join(',')}`);
}

export async function askChat(question: string, stockCodes?: string[]) {
  return http<ChatQueryResponse>('/api/v1/chat/query', {
    method: 'POST',
    body: JSON.stringify({
      session_id: 'web-session',
      question,
      stock_codes: stockCodes,
      top_k: 8,
    }),
  });
}

export async function runPrediction(stockCode: string) {
  return http<PredictionRunResponse>(`/api/v1/predictions/${stockCode}`, {
    method: 'POST',
  });
}
