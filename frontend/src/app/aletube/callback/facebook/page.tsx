'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function FacebookCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (code) {
      // Enviar o código para o backend processar
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://alessandro2090-bestpricetoday-api.hf.space'}/api/v1/aletube/callback/facebook?code=${code}&state=${state}`)
        .then(res => res.json())
        .then(data => {
          console.log('Facebook callback success:', data);
          // Redirecionar para a página aletubegames
          router.push('/aletubegames');
        })
        .catch(error => {
          console.error('Facebook callback error:', error);
          router.push('/aletubegames?error=facebook_callback_failed');
        });
    } else {
      console.error('No code in Facebook callback');
      router.push('/aletubegames?error=no_code');
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