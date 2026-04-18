const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

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

export async function getCompanies(limit = 80) {
  return http<any[]>(`/api/v1/companies?limit=${limit}&offset=0`);
}

export async function getDashboardOverview() {
  return http<any>('/api/v1/dashboard/overview');
}

export async function getCompanyProfile(stockCode: string) {
  return http<any>(`/api/v1/companies/${stockCode}/profile`);
}

export async function compareCompanies(codes: string[]) {
  return http<any>(`/api/v1/compare?codes=${codes.join(',')}`);
}

export async function askChat(question: string, stockCodes?: string[]) {
  return http<any>('/api/v1/chat/query', {
    method: 'POST',
    body: JSON.stringify({
      session_id: 'web-session',
      question,
      stock_codes: stockCodes,
      top_k: 8,
    }),
  });
}
