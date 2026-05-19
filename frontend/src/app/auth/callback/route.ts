import { NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://alessandro2090-bestpricetoday-api.hf.space'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const error = searchParams.get('error')

  if (error || !code) {
    return new NextResponse(`<h2>❌ Erro: ${error || 'code ausente'}</h2>`, {
      status: 400,
      headers: { 'Content-Type': 'text/html' },
    })
  }

  const params = new URLSearchParams({ code })
  if (state) params.set('state', state)

  // Redirect server-side — instantâneo, code não expira
  return NextResponse.redirect(`${API_BASE}/api/v1/auth/ml/callback?${params.toString()}`)
}
