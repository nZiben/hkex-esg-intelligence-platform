'use client';

import { useDeferredValue, useState } from 'react';
import type { CompanySummary } from '@/lib/api';

type CompanyPickerProps = {
  companies: CompanySummary[];
  selectedCodes: string[];
  onChange: (codes: string[]) => void;
  label: string;
  placeholder: string;
  hint?: string;
  maxSelect?: number;
};

export function CompanyPicker({
  companies,
  selectedCodes,
  onChange,
  label,
  placeholder,
  hint,
  maxSelect,
}: CompanyPickerProps) {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);

  const selectedCompanies = selectedCodes
    .map((code) => companies.find((company) => company.stock_code === code))
    .filter(Boolean) as CompanySummary[];

  const normalizedQuery = deferredQuery.trim().toLowerCase();
  const filteredCompanies = companies
    .filter((company) => !selectedCodes.includes(company.stock_code))
    .filter((company) => {
      if (!normalizedQuery) {
        return true;
      }

      const haystack = [
        company.stock_code,
        company.company_name,
        company.industry || '',
        company.esg_rating_raw || '',
      ]
        .join(' ')
        .toLowerCase();

      return haystack.includes(normalizedQuery);
    })
    .slice(0, 8);

  const addCompany = (stockCode: string) => {
    if (selectedCodes.includes(stockCode)) {
      return;
    }
    if (maxSelect && selectedCodes.length >= maxSelect) {
      return;
    }

    onChange([...selectedCodes, stockCode]);
    setQuery('');
  };

  const removeCompany = (stockCode: string) => {
    onChange(selectedCodes.filter((code) => code !== stockCode));
  };

  const selectionLimitReached = Boolean(maxSelect && selectedCodes.length >= maxSelect);

  return (
    <div className="company-picker">
      <div className="field-head">
        <label className="field-label">{label}</label>
        {hint ? <p className="field-hint">{hint}</p> : null}
      </div>

      <div className="picker-selected">
        {selectedCompanies.length ? (
          selectedCompanies.map((company) => (
            <button
              key={company.stock_code}
              type="button"
              className="company-chip"
              onClick={() => removeCompany(company.stock_code)}
            >
              <span>{company.company_name}</span>
              <strong>{company.stock_code}</strong>
            </button>
          ))
        ) : (
          <p className="empty-note">No companies selected yet.</p>
        )}
      </div>

      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={selectionLimitReached ? 'Selection limit reached' : placeholder}
        disabled={selectionLimitReached}
      />

      {!selectionLimitReached ? (
        <div className="picker-results">
          {filteredCompanies.length ? (
            filteredCompanies.map((company) => (
              <button
                key={company.stock_code}
                type="button"
                className="picker-option"
                onClick={() => addCompany(company.stock_code)}
              >
                <span className="picker-option-title">
                  {company.company_name} <strong>{company.stock_code}</strong>
                </span>
                <span className="picker-option-meta">
                  {company.industry || 'Unknown industry'}
                  {company.esg_rating_raw ? ` • ${company.esg_rating_raw}` : ''}
                </span>
              </button>
            ))
          ) : (
            <p className="empty-note">No matching companies.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
