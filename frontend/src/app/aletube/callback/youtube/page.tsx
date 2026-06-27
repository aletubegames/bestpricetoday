'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { API_BASE as API, apiFetch } from '@/lib/api';

function YouTubeCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const code  = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    if (error) {
      setStatus('error');
      setMessage(error === 'access_denied' ? 'Você cancelou a conexão com o YouTube.' : `Erro YouTube: ${error}`);
      return;
    }

    if (!code) {
      setStatus('error');
      setMessage('Código de autorização não encontrado.');
      return;
    }

    apiFetch(`${API}/api/v1/aletube/callback/youtube?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state || '')}`)
      .then(async res => {
        if (!res.ok) {
          const err = await res.json().catch(() => null) as { detail?: string } | null;
          throw new Error(err?.detail || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        setStatus('success');
        setMessage(`Canal "${data.channel_title || 'YouTube'}" conectado com sucesso!`);
        if (window.opener) {
          window.opener.postMessage({ type: 'YOUTUBE_AUTH_SUCCESS', data }, '*');
          setTimeout(() => window.close(), 2000);
        } else {
          setTimeout(() => router.push('/aletubegames'), 2000);
        }
      })
      .catch(err => {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Erro ao conectar com YouTube');
        if (window.opener) {
          window.opener.postMessage({ type: 'YOUTUBE_AUTH_ERROR', error: err instanceof Error ? err.message : 'Erro' }, '*');
        }
      });
  }, [searchParams, router]);

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#f0f4ff', padding: 24,
    }}>
      <div style={{
        background: '#ffffff', border: '1px solid rgba(255,0,0,0.2)', borderRadius: 20,
        padding: 32, maxWidth: 380, width: '100%', textAlign: 'center',
      }}>
        <div style={{
          width: 56, height: 56, borderRadius: 16, margin: '0 auto 20px',
          background: '#ff0000', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 28, color: '#fff',
        }}>▶</div>

        {status === 'loading' && (
          <>
            <h2 style={{ color: '#1a1a2e', fontSize: 18, marginBottom: 8 }}>Conectando YouTube...</h2>
            <p style={{ color: '#6b6b8a', fontSize: 13 }}>Aguarde enquanto autorizamos o canal</p>
            <div style={{ marginTop: 20 }}>
              <div style={{
                width: 36, height: 36, border: '3px solid #ff0000',
                borderTopColor: 'transparent', borderRadius: '50%',
                animation: 'spin 0.8s linear infinite', margin: '0 auto',
              }} />
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{ fontSize: 40, marginBottom: 12 }}>✅</div>
            <h2 style={{ color: '#00e5a0', fontSize: 18, marginBottom: 8 }}>YouTube conectado!</h2>
            <p style={{ color: '#1a1a2e', fontSize: 14 }}>{message}</p>
            <p style={{ color: '#6b6b8a', fontSize: 12, marginTop: 8 }}>
              {window.opener ? 'Esta janela fechará automaticamente...' : 'Redirecionando...'}
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ fontSize: 40, marginBottom: 12 }}>❌</div>
            <h2 style={{ color: '#f87171', fontSize: 18, marginBottom: 8 }}>Erro na conexão</h2>
            <p style={{ color: '#4a4a6a', fontSize: 13, marginBottom: 20 }}>{message}</p>
            <button
              onClick={() => window.opener ? window.close() : router.push('/aletubegames')}
              style={{
                padding: '10px 24px', borderRadius: 10,
                background: 'rgba(255,0,0,0.1)', border: '1px solid rgba(255,0,0,0.2)',
                color: '#4a4a6a', cursor: 'pointer', fontSize: 13,
              }}
            >
              {window.opener ? 'Fechar' : 'Voltar'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function YouTubeCallbackPage() {
  return (
    <Suspense fallback={
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#f0f4ff', color: '#6b6b8a', fontSize: 14,
      }}>
        Carregando...
      </div>
    }>
      <YouTubeCallbackContent />
    </Suspense>
  );
}
