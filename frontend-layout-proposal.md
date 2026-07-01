# Proposta de Melhorias de Layout — BestPriceToday

> **Escopo:** melhorias visuais e de UX no frontend. **Nenhuma lógica de negócio será alterada.**
> Foco: consistência visual, hierarquia, mobile-first e manutenibilidade.

---

## 1. Resumo executivo

O frontend atual já tem uma identidade visual coerente (paleta roxo + laranja, tipografia Syne/DM Sans, cards arredondados), mas acumulou inconsistências porque as páginas foram evoluindo separadamente. A proposta abaixo organiza o layout em 5 frentes:

1. **Unificação do header** (novo item principal)
2. Home page
3. Página de oferta (`/oferta/[code]`)
4. Página de produto (`/produto/[query]`)
5. Páginas internas (`/afiliados`, `/cupons`, `/admin`, `/dashboard`)
6. Sistema de design e tokens globais

---

## 2. Unificação do Header (item principal)

### 2.1 Por que unificar

Hoje cada página tem seu próprio header:

- Home: logo 3D + badge + Alertas + Auth
- Oferta: logo minimalista + "Redirecionamento seguro"
- Produto: outro header
- Afiliados: header de admin
- Cupons: apenas botão "Voltar"

Isso cria navegação inconsistente, duplica código e dificulta manutenção. Tecnicamente o header pode — e deve — ser um componente compartilhado.

### 2.2 Estrutura proposta

Criar `frontend/src/components/layout/Header.tsx` com 3 variantes:

| Variante | Uso | Elementos |
|---|---|---|
| `default` | Home, produto, cupons, categorias, marcas | Logo + busca + Alertas + Cupons + Auth |
| `minimal` | `/oferta/[code]` | Logo + "Voltar para home" + badge de segurança |
| `admin` | `/afiliados`, `/admin`, `/dashboard` | Logo + links admin (Dashboard, Afiliados, AleTubeGames) + logout |

### 2.3 Implementação sugerida

1. Criar `frontend/src/components/layout/Header.tsx`.
2. Mover o `AuthButton` atual para dentro do Header.
3. Adicionar o Header no `layout.tsx` ou importar nas páginas que precisam dele.
4. Usar `<Link>` do Next.js para navegação interna.
5. Criar `frontend/src/components/layout/Header.module.css` para estilos compartilhados.

### 2.4 Cuidado especial

A página `/oferta/[code]` é uma página de conversão. Deve manter o header minimalista para não roubar atenção do CTA "Ver oferta". Por isso a variante `minimal` é necessária.

---

## 3. Home Page

### 3.1 Simplificar o Hero

**Objetivo:** a barra de busca deve ser o protagonista.

**Alterações:**
- Remover ou reduzir o logo 3D flutuante com glow/anel.
- Manter: badge social proof, título, subtítulo, busca.
- Aumentar largura máxima da SearchBar para `680px`.
- Reduzir altura da SearchBar em mobile para `56px`.

**Layout sugerido:**
```
[Header unificado]
[Hero]
  Badge: "⚡ Comparação em tempo real"
  Título: "Menor preço do Brasil"
  Subtítulo
  SearchBar
  Trending pills (flex-wrap centralizado)
[Resultados / Landing]
```

### 3.2 Cards de resultado mais escaneáveis

- Mover provider para chip no canto superior direito.
- Destacar o preço mais baixo em verde (`#00b894`).
- Aumentar hover: `translateY(-3px)` + sombra mais forte.
- Padronizar fundo da imagem com padding fixo.

### 3.3 Ritmo visual entre seções

Alternar fundos para criar "respiração" na página:

| Seção | Fundo |
|---|---|
| Hero | `--bg` (#eeeef8) |
| Ofertas em destaque + Categorias | branco |
| Como funciona | `--bg` |
| Stats + Gráfico | branco |
| Depoimentos | `--bg` |
| FAQ | branco |
| Trust Badges | `--bg` |
| Footer | escuro (#1a1a2e) |

### 3.4 Footer profissional

- Fundo escuro com 3 colunas: marca, links úteis, contato/legal.
- Separar links de ação (alertas, cupons) de links legais (termos, privacidade).

### 3.5 Pills de trending em mobile

- Substituir grid `auto-fit` por scroll horizontal com `overflow-x: auto`.
- Evita que fiquem 1 coluna larga ou 2 colunas apertadas.

---

## 4. Página de Oferta (`/oferta/[code]`)

### 4.1 CTA mais dominante

- Aumentar botão "Ver oferta na {provider}" para quase toda a largura.
- Usar cor da loja no CTA:
  - Amazon: laranja
  - Mercado Livre: amarelo
  - Shopee: laranja/vermelho
  - Outros: roxo padrão
- Adicionar microcopy abaixo: *"Você será redirecionado para {provider} com segurança."*

### 4.2 Badges de confiança acima do CTA

Adicionar uma linha com 3 micro-badges:
- ✅ Compra na loja oficial
- 🔄 Preço atualizado agora
- 🔒 Redirecionamento seguro

### 4.3 Histórico de preço em card separado

- Mover o `PriceHistoryPublic` para um card próprio abaixo da descrição.
- Título: "📉 Histórico de preço".

---

## 5. Página de Produto (`/produto/[query]`)

### 5.1 Melhorar o "melhor preço"

- Card do primeiro resultado (`cardBest`) com fundo levemente verde.
- Badge flutuante: "🏆 Menor preço".
- CTA em verde em vez de roxo.

### 5.2 Grid e imagens

- Em telas grandes, manter 4 colunas com cards mais compactos verticalmente.
- Aumentar altura da imagem para `180px` para produtos parecerem mais reais.

---

## 6. Páginas Internas

### 6.1 `/afiliados`

- **Tabs por provider com cores de identidade:** ML amarelo, Shopee laranja, AliExpress vermelho, Amazon azul, Lomadee roxo.
- **Cards verticais:** imagem grande em cima, título, preço, CTA embaixo (substituir layout horizontal com imagem 80×80).
- **Sticky bar:** barra de busca/filtros fixa ao rolar para facilitar paginação.

### 6.2 `/cupons`

- Destacar o cupom com card gradiente sutil (rosa/vermelho claro).
- Código do cupom em fonte monospace maior.
- Botão "Copiar" ao lado com destaque.
- Mover badge de desconto para canto superior direito.

### 6.3 `/admin` e `/dashboard`

- Aplicar header `admin` compartilhado.
- Padronizar tabelas com a classe `.table-wrap` já existente.
- Usar cards consistentes com o restante do site.

---

## 7. Sistema de Design e Tokens Globais

### 7.1 Expandir `globals.css`

Adicionar tokens padronizados:

```css
:root {
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --shadow-sm: 0 2px 8px rgba(26, 26, 46, 0.04);
  --shadow-md: 0 8px 24px rgba(26, 26, 46, 0.08);
  --shadow-lg: 0 16px 48px rgba(26, 26, 46, 0.12);
  --spacing-section: 72px;
  --spacing-card: 16px;
}
```

### 7.2 Componente `Section` compartilhado

Criar wrapper reutilizável:

```tsx
// src/components/layout/Section.tsx
export default function Section({ children, bg }: { children: React.ReactNode; bg?: "white" | "muted" | "dark" }) {
  return <section className={`${styles.section} ${styles[bg || "white"]}`}>{children}</section>;
}
```

Regras:
- `max-width: 1200px`
- `padding: 0 24px`
- `margin-bottom: var(--spacing-section)`

### 7.3 Padronizar botões

Criar 3 classes globais:

- `.btn-primary` — roxo, CTA principal.
- `.btn-provider` — cor da loja (Amazon, ML, Shopee etc.).
- `.btn-ghost` — borda, ações secundárias.

### 7.4 Migrar inline styles para CSS Modules

Componentes com muitos estilos inline:
- `FAQ.tsx`
- `HowItWorks.tsx`
- `FeaturedOffers.tsx`
- `Testimonials.tsx`
- `TrustBadges.tsx`
- `SearchBar.tsx` (parcial)

**Benefício:** menos re-render, melhor manutenção, consistência.

---

## 8. Roadmap de implementação

### Fase 1 — Fundação (alto impacto, baixo risco)

1. Criar `Header.tsx` compartilhado com variantes `default`, `minimal`, `admin`.
2. Substituir headers das páginas de navegação pela variante `default`.
3. Manter `/oferta` com a variante `minimal`.
4. Criar tokens de design em `globals.css`.

### Fase 2 — Home e Cards

5. Simplificar o Hero da home.
6. Padronizar cards de resultado (home + produto).
7. Aplicar alternância de fundos nas seções da home.
8. Melhorar footer.

### Fase 3 — Páginas de conversão

9. Refinar CTA e badges de confiança em `/oferta`.
10. Melhorar card "melhor preço" em `/produto/[query]`.

### Fase 4 — Internas

11. Redesenhar `/afiliados` (tabs coloridas, cards verticais, sticky filters).
12. Refinar `/cupons` (cupom destacado).

### Fase 5 — Refatoração técnica

13. Migrar inline styles dos componentes home para CSS Modules.
14. Criar componente `Section` reutilizável.
15. Padronizar botões com classes globais.

---

## 9. Matriz de prioridade

| # | Melhoria | Impacto Visual | Esforço | Recomendado |
|---|---|---|---|---|
| 1 | Header compartilhado | Alto | Médio | ⭐ Essencial |
| 2 | Simplificar Hero | Alto | Médio | ⭐ Essencial |
| 3 | Alternância de fundos na home | Alto | Baixo | ⭐ Essencial |
| 4 | Padronizar cards de resultado | Alto | Médio | ⭐ Essencial |
| 5 | CTA colorido por provider em `/oferta` | Médio | Baixo | Sim |
| 6 | Footer profissional | Médio | Baixo | Sim |
| 7 | Tokens de design em `globals.css` | Médio | Baixo | Sim |
| 8 | Cards verticais em `/afiliados` | Médio | Médio | Sim |
| 9 | Cupom destacado em `/cupons` | Baixo | Baixo | Sim |
| 10 | Migrar inline styles → CSS Modules | Médio | Alto | Fase 2 |

---

## 10. Próximos passos recomendados

Se for começar agora, a ordem sugerida é:

1. **Header compartilhado** (unifica navegação e reduz código duplicado).
2. **Hero simplificado** (aumenta foco na busca).
3. **Alternância de fundos na home** (melhora ritmo visual sem mudar conteúdo).

Essas 3 mudanças já dão uma cara muito mais profissional ao site com esforço controlado.
