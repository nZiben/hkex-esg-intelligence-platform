'use client';

import { startTransition, useEffect, useRef, useState } from 'react';
import { CitationList } from '@/components/CitationList';
import { CompanyPicker } from '@/components/CompanyPicker';
import { askChat, getCompanies, type ChatQueryResponse, type CompanySummary } from '@/lib/api';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: ChatQueryResponse['citations'];
  confidence?: number;
  latencyMs?: number;
  followUps?: string[];
};

const starterPrompts = [
  'Which company currently looks strongest on governance disclosures?',
  'Compare environmental disclosure tone between two utility companies.',
  'Summarize the ESG profile of the selected company in plain business language.',
];

export default function ChatPage() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'I can help you inspect ESG signals, compare companies, and explain disclosure patterns with citations. Search for one or more companies on the left, or ask broadly across the dataset.',
    },
  ]);

  const threadEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let mounted = true;

    getCompanies()
      .then((payload) => {
        if (mounted) {
          setCompanies(payload);
          const codesFromUrl = ((typeof window !== 'undefined'
            ? new URLSearchParams(window.location.search).get('codes')
            : '') || '')
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean)
            .slice(0, 4);

          if (codesFromUrl.length) {
            setSelectedCodes(codesFromUrl);
          }
        }
      })
      .catch((err: Error) => {
        if (mounted) {
          setError(err.message);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, loading]);

  const submitQuestion = async (input?: string) => {
    const prompt = (input ?? question).trim();
    if (!prompt || loading) {
      return;
    }

    setError(null);
    setLoading(true);

    setMessages((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        role: 'user',
        content: prompt,
      },
    ]);
    setQuestion('');

    try {
      const payload = await askChat(prompt, selectedCodes.length ? selectedCodes : undefined);
      startTransition(() => {
        setMessages((current) => [
          ...current,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: payload.answer,
            citations: payload.citations,
            confidence: payload.confidence,
            latencyMs: payload.latency_ms,
            followUps: payload.follow_up_questions,
          },
        ]);
      });
    } catch (err: any) {
      setError(err.message || 'Chat request failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="chat-layout">
      <aside className="chat-sidebar panel">
        <div className="section-head">
          <div>
            <span className="eyebrow">Conversation scope</span>
            <h2>Search companies, don&apos;t type IDs</h2>
          </div>
          <p className="section-copy">
            Scope the conversation to one or more issuers if you want a more focused answer. Leave it empty to search
            across the ingested dataset.
          </p>
        </div>

        <CompanyPicker
          companies={companies}
          selectedCodes={selectedCodes}
          onChange={setSelectedCodes}
          label="Focus companies"
          placeholder="Search by company name, code, industry, or rating"
          hint="This replaces the old raw stock-code input."
          maxSelect={4}
        />

        <div className="panel subtle-panel">
          <span className="eyebrow">Starter prompts</span>
          <div className="prompt-stack">
            {starterPrompts.map((prompt) => (
              <button key={prompt} type="button" className="ghost-button" onClick={() => submitQuestion(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="chat-main">
        <header className="chat-head panel">
          <div>
            <span className="eyebrow">Analyst chat</span>
            <h2>Ask for ESG insight, not just document search.</h2>
          </div>
          <p className="section-copy">
            The assistant responds with evidence-backed summaries, then suggests follow-up angles so research can keep
            moving.
          </p>
        </header>

        <div className="chat-thread panel">
          {messages.map((message) => (
            <article key={message.id} className={`message-card ${message.role}`}>
              <div className="message-meta">
                <span>{message.role === 'assistant' ? 'ESG analyst assistant' : 'You'}</span>
                {message.confidence ? <span>Confidence {message.confidence}</span> : null}
                {message.latencyMs ? <span>{message.latencyMs} ms</span> : null}
              </div>

              <div className="message-body">
                <p style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>
                {message.citations?.length ? <CitationList citations={message.citations} /> : null}
                {message.followUps?.length ? (
                  <div className="followup-row">
                    {message.followUps.map((item) => (
                      <button key={item} type="button" className="ghost-button" onClick={() => submitQuestion(item)}>
                        {item}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </article>
          ))}

          {loading ? (
            <article className="message-card assistant pending">
              <div className="message-meta">
                <span>ESG analyst assistant</span>
              </div>
              <div className="typing-row">
                <span />
                <span />
                <span />
              </div>
            </article>
          ) : null}

          <div ref={threadEndRef} />
        </div>

        <footer className="composer-card panel">
          <div className="composer-head">
            <div>
              <span className="eyebrow">Compose</span>
              <p className="section-copy">
                {selectedCodes.length
                  ? `Scoped to ${selectedCodes.length} selected compan${selectedCodes.length > 1 ? 'ies' : 'y'}.`
                  : 'No company scope selected. The assistant will search across the whole dataset.'}
              </p>
            </div>
            {error ? <p className="error-banner">{error}</p> : null}
          </div>

          <div className="composer-row">
            <textarea
              rows={4}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask for a summary, comparison, risk signal, or cited explanation..."
            />
            <button type="button" className="composer-button" onClick={() => submitQuestion()} disabled={loading}>
              {loading ? 'Thinking…' : 'Send'}
            </button>
          </div>
        </footer>
      </section>
    </section>
  );
}
