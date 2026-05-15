'use client'
import { Suspense } from 'react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'https://alessandro2090-bestpricetoday-api.hf.space'

function AuthCallbackInner() {
  const params = useSearchParams()
  const [status, setStatus] = useState('Processando...')

  useEffect(() => {
    const code = params.get('code')
    const error = params.get('error')

    if (error) {
      setStatus(`Erro: ${error}`)
      return
    }
    if (!code) {
      setStatus('Code ausente na URL.')
      return
    }

    window.location.href = `${API}/api/v1/auth/ml/callback?code=${code}`
  }, [params])

  return (
    <div style={{ fontFamily: 'monospace', padding: '2rem', background: '#111', color: '#0f0', minHeight: '100vh' }}>
      <h2>🔐 Autenticação Mercado Livre</h2>
      <p>{status}</p>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div style={{ fontFamily: 'monospace', padding: '2rem', background: '#111', color: '#0f0', minHeight: '100vh' }}>
        <p>Carregando...</p>
      </div>
    }>
      <AuthCallbackInner />
    </Suspense>
  )
}
