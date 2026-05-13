'use client'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'https://alessandro2090-bestpricetoday-api.hf.space'

export default function AuthCallback() {
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

    // Repassa o code pro backend
    fetch(`${API}/auth/ml/callback?code=${code}`)
      .then(r => r.text())
      .then(html => {
        // Redireciona para o backend que mostra os tokens
        window.location.href = `${API}/auth/ml/callback?code=${code}`
      })
      .catch(e => setStatus(`Erro: ${e.message}`))
  }, [params])

  return (
    <div style={{ fontFamily: 'monospace', padding: '2rem', background: '#111', color: '#0f0', minHeight: '100vh' }}>
      <h2>🔐 Autenticação Mercado Livre</h2>
      <p>{status}</p>
    </div>
  )
}
