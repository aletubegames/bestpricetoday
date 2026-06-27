'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiFetch, API_BASE } from "@/lib/api";

function FacebookCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (code) {
      const API = API_BASE;
      apiFetch(`${API}/api/v1/aletube/callback/facebook?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state || '')}`)
        .then(async res => {
          if (!res.ok) {
            const err = await res.json().catch(() => null) as { detail?: string } | null;
            throw new Error(err?.detail || `HTTP ${res.status}`);
          }
          return res.json();
        })
        .then(data => {
          console.log('Facebook callback success:', data);
          if (window.opener) {
            window.opener.postMessage({ type: 'FACEBOOK_AUTH_SUCCESS', data }, '*');
            setTimeout(() => window.close(), 1500);
          } else {
            router.push('/aletubegames?connected=facebook');
          }
        })
        .catch(error => {
          console.error('Facebook callback error:', error);
          const msg = error instanceof Error ? error.message : 'Erro desconhecido';
          if (window.opener) {
            window.opener.postMessage({ type: 'FACEBOOK_AUTH_ERROR', error: msg }, '*');
          }
          router.push(`/aletubegames?error=${encodeURIComponent(msg)}`);
        });
    } else {
      const errorParam = searchParams.get('error') || 'no_code';
      console.error('No code in Facebook callback, error:', errorParam);
      router.push(`/aletubegames?error=${encodeURIComponent(errorParam)}`);
    }
  }, [searchParams, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Processando conexão com Facebook...</p>
      </div>
    </div>
  );
}

export default function FacebookCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    }>
      <FacebookCallbackContent />
    </Suspense>
  );
}