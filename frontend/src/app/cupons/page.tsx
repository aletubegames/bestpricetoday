"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import Header from "@/components/layout/Header"
import { API_BASE } from "@/lib/api"
import { trackCopyCoupon } from "@/lib/analytics"
import styles from "./cupons.module.css"

interface CouponProduct {
  id: string
  title: string
  product_url: string
  image_url: string | null
  price: number | null
  ml_code: string | null
  coupon: {
    code: string
    discount_text: string | null
    discount_percent: number | null
    discount_value: number | null
    store_name: string | null
    expires_at: string | null
    conditions: string | null
  }
}

interface StoreInfo {
  store_name: string
  product_count: number
  max_discount: number | null
  expires_soonest: string | null
}

interface ApiResponse {
  total: number
  products: CouponProduct[]
}

const PAGE_SIZE = 24

type SortOption = "expires_soon" | "biggest_discount" | "lowest_price" | "highest_price" | "newest"

const SORT_LABELS: Record<SortOption, string> = {
  expires_soon: "Vence em breve",
  biggest_discount: "Maior desconto",
  lowest_price: "Menor preço",
  highest_price: "Maior preço",
  newest: "Mais recentes",
}

export default function CuponsPage() {
  const [products, setProducts] = useState<CouponProduct[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  // Filtros
  const [stores, setStores] = useState<StoreInfo[]>([])
  const [selectedStore, setSelectedStore] = useState<string | null>(null)
  const [sort, setSort] = useState<SortOption>("expires_soon")
  const [minDiscount, setMinDiscount] = useState<string>("")
  const [maxPrice, setMaxPrice] = useState<string>("")
  const [showFilters, setShowFilters] = useState(false)

  const fetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Busca lojas
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/affiliate/coupons/stores`)
      .then((r) => r.json())
      .then((data) => setStores(data.stores || []))
      .catch(() => {})
  }, [])

  const buildUrl = (page: number) => {
    const params = new URLSearchParams()
    params.set("limit", String(PAGE_SIZE))
    params.set("offset", String((page - 1) * PAGE_SIZE))
    params.set("sort", sort)
    if (selectedStore) params.set("store", selectedStore)
    if (minDiscount) params.set("min_discount", minDiscount)
    if (maxPrice) params.set("max_price", maxPrice)
    return `${API_BASE}/api/v1/affiliate/coupons/products?${params.toString()}`
  }

  const fetchProducts = useCallback(
    async (page: number = 1) => {
      setLoading(true)
      try {
        const res = await fetch(buildUrl(page))
        if (!res.ok) throw new Error("Failed to fetch")
        const data: ApiResponse = await res.json()
        setProducts(data.products)
        setTotal(data.total)
        setCurrentPage(page)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    },
    [sort, selectedStore, minDiscount, maxPrice]
  )

  // Refetch quando filtros mudam (com debounce)
  useEffect(() => {
    if (fetchTimer.current) clearTimeout(fetchTimer.current)
    fetchTimer.current = setTimeout(() => {
      fetchProducts(1)
    }, 300)
    return () => {
      if (fetchTimer.current) clearTimeout(fetchTimer.current)
    }
  }, [sort, selectedStore, minDiscount, maxPrice])

  const handleCopy = (code: string, product?: CouponProduct) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    trackCopyCoupon({
      coupon_code: code,
      discount_text: product?.coupon.discount_text || undefined,
      store_name: product?.coupon.store_name || undefined,
    })
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const formatDate = (iso: string | null) => {
    if (!iso) return null
    const d = new Date(iso)
    const now = new Date()
    const diff = d.getTime() - now.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    if (days < 0) return "Vencido"
    if (days === 0) return "Vence hoje!"
    if (days === 1) return "Vence amanhã"
    if (days <= 7) return `Vence em ${days} dias`
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })
  }

  const formatPrice = (price: number | null) => {
    if (price == null) return null
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(price)
  }

  const clearFilters = () => {
    setSelectedStore(null)
    setSort("expires_soon")
    setMinDiscount("")
    setMaxPrice("")
  }

  const hasActiveFilters = selectedStore || minDiscount || maxPrice || sort !== "expires_soon"
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <>
      <Header variant="default" />
      <div className={styles.container}>
        {/* Header */}
        <div className={styles.header}>
        <h1 className={styles.title}>
          <span className={styles.titleIcon}>🏷️</span>
          Produtos com Cupom
        </h1>
        <p className={styles.subtitle}>
          {total > 0
            ? `${total} produtos com desconto extra no checkout`
            : "Carregando produtos com cupom..."}
        </p>
      </div>

      {/* Barra de filtros */}
      <div className={styles.filterBar}>
        {/* Ordenação */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Ordenar:</label>
          <select
            className={styles.select}
            value={sort}
            onChange={(e) => setSort(e.target.value as SortOption)}
          >
            {Object.entries(SORT_LABELS).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Desconto mínimo */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Desconto mín.:</label>
          <select
            className={styles.select}
            value={minDiscount}
            onChange={(e) => setMinDiscount(e.target.value)}
          >
            <option value="">Qualquer</option>
            <option value="5">5%+</option>
            <option value="10">10%+</option>
            <option value="15">15%+</option>
            <option value="20">20%+</option>
            <option value="25">25%+</option>
            <option value="30">30%+</option>
            <option value="50">50%+</option>
          </select>
        </div>

        {/* Preço máximo */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Preço máx.:</label>
          <select
            className={styles.select}
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
          >
            <option value="">Qualquer</option>
            <option value="50">R$ 50</option>
            <option value="100">R$ 100</option>
            <option value="200">R$ 200</option>
            <option value="500">R$ 500</option>
            <option value="1000">R$ 1.000</option>
            <option value="2000">R$ 2.000</option>
          </select>
        </div>

        {/* Toggle filtros mobile */}
        <button
          className={styles.filterToggle}
          onClick={() => setShowFilters(!showFilters)}
        >
          {showFilters ? "▲ Fechar lojas" : "▼ Filtrar por loja"}
        </button>

        {/* Limpar filtros */}
        {hasActiveFilters && (
          <button className={styles.clearBtn} onClick={clearFilters}>
            ✕ Limpar filtros
          </button>
        )}
      </div>

      {/* Filtro por loja (chips) */}
      {showFilters && stores.length > 0 && (
        <div className={styles.storeFilters}>
          <button
            className={`${styles.storeChip} ${!selectedStore ? styles.storeChipActive : ""}`}
            onClick={() => setSelectedStore(null)}
          >
            Todas as lojas ({total})
          </button>
          {stores.map((s) => (
            <button
              key={s.store_name}
              className={`${styles.storeChip} ${selectedStore === s.store_name ? styles.storeChipActive : ""}`}
              onClick={() => setSelectedStore(s.store_name)}
            >
              {s.store_name.replace(/-/g, " ")} ({s.product_count})
              {s.max_discount && (
                <span className={styles.storeChipDiscount}> • até {s.max_discount}%</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Resumo de filtros ativos */}
      {(selectedStore || minDiscount || maxPrice) && (
        <div className={styles.activeFilters}>
          <span className={styles.activeFilterLabel}>Filtros ativos:</span>
          {selectedStore && (
            <span className={styles.activeFilterTag}>
              🏪 {selectedStore.replace(/-/g, " ")}
              <button onClick={() => setSelectedStore(null)}>✕</button>
            </span>
          )}
          {minDiscount && (
            <span className={styles.activeFilterTag}>
              💰 {minDiscount}%+ desconto
              <button onClick={() => setMinDiscount("")}>✕</button>
            </span>
          )}
          {maxPrice && (
            <span className={styles.activeFilterTag}>
              📦 até R$ {maxPrice}
              <button onClick={() => setMaxPrice("")}>✕</button>
            </span>
          )}
        </div>
      )}

      {/* Grid de produtos */}
      <div className={styles.grid}>
        {products.map((product) => {
          const expires = formatDate(product.coupon.expires_at)
          const isExpiringSoon =
            expires === "Vence hoje!" || expires === "Vence amanhã"
          const price = formatPrice(product.price)
          const discount = product.coupon.discount_text || ""

          // Calcula preço com desconto
          let finalPrice = null
          if (product.price && product.coupon.discount_percent) {
            finalPrice = product.price * (1 - product.coupon.discount_percent / 100)
          } else if (product.price && product.coupon.discount_value) {
            finalPrice = product.price - product.coupon.discount_value
          }

          return (
            <div key={product.id} className={styles.card}>
              {/* Badge de desconto */}
              <div className={styles.discountBadge}>{discount}</div>

              {/* Imagem */}
              <a
                href={product.product_url}
                target="_blank"
                rel="noopener noreferrer sponsored"
                className={styles.imageLink}
              >
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.title}
                    className={styles.image}
                    loading="lazy"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none"
                      const parent = (e.target as HTMLImageElement).parentElement
                      if (parent) {
                        parent.classList.add(styles.imageFallback)
                        parent.setAttribute("data-letter", product.title.charAt(0).toUpperCase())
                      }
                    }}
                  />
                ) : (
                  <div className={`${styles.imagePlaceholder} ${styles.imageFallback}`} data-letter={product.title.charAt(0).toUpperCase()}>
                    <span>{product.title.charAt(0).toUpperCase()}</span>
                  </div>
                )}
              </a>

              {/* Info */}
              <div className={styles.info}>
                <a
                  href={product.product_url}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className={styles.productTitle}
                >
                  {product.title}
                </a>

                {/* Loja */}
                {product.coupon.store_name && (
                  <span
                    className={styles.store}
                    onClick={() => setSelectedStore(product.coupon.store_name)}
                    style={{ cursor: "pointer" }}
                  >
                    🏪 {product.coupon.store_name.replace(/-/g, " ")}
                  </span>
                )}

                {/* Preço */}
                {price && (
                  <div className={styles.priceRow}>
                    <span className={styles.priceOriginal}>{price}</span>
                    {finalPrice && finalPrice > 0 && (
                      <span className={styles.priceFinal}>
                        {formatPrice(finalPrice)}
                      </span>
                    )}
                  </div>
                )}

                {/* Cupom */}
                <div className={styles.couponBox}>
                  {product.coupon.code.startsWith("MLC-") ? (
                    <div className={styles.couponInfo}>
                      <span className={styles.couponLabel}>
                        Cupom Mercado Livre — ative na sua conta ao abrir a oferta
                      </span>
                    </div>
                  ) : (
                    <>
                      <div className={styles.couponInfo}>
                        <span className={styles.couponLabel}>Cupom:</span>
                        <code className={styles.couponCode}>{product.coupon.code}</code>
                      </div>
                      <button
                        className={styles.copyBtn}
                        onClick={() => handleCopy(product.coupon.code, product)}
                      >
                        {copiedCode === product.coupon.code ? "✓" : "Copiar"}
                      </button>
                    </>
                  )}
                </div>

                {/* Vencimento */}
                {expires && (
                  <span
                    className={`${styles.expires} ${
                      isExpiringSoon ? styles.expiresSoon : ""
                    }`}
                  >
                    ⏰ {expires}
                  </span>
                )}

                {/* CTA */}
                <a
                  href={product.product_url}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className={styles.cta}
                >
                  🛒 Ver na loja
                </a>
              </div>
            </div>
          )
        })}
      </div>

      {/* Loading */}
      {loading && (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Carregando...</p>
        </div>
      )}

      {/* Paginação */}
      {!loading && totalPages > 1 && products.length > 0 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            disabled={currentPage === 1}
            onClick={() => { fetchProducts(currentPage - 1); window.scrollTo({ top: 0, behavior: "smooth" }) }}
          >
            ‹ Anterior
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
            .map((p, idx, arr) => (
              <span key={p} className={styles.pageBtnWrap}>
                {idx > 0 && arr[idx - 1] !== p - 1 && <span className={styles.pageDots}>…</span>}
                <button
                  className={`${styles.pageNum} ${p === currentPage ? styles.pageActive : ""}`}
                  onClick={() => { fetchProducts(p); window.scrollTo({ top: 0, behavior: "smooth" }) }}
                >
                  {p}
                </button>
              </span>
            ))}
          <button
            className={styles.pageBtn}
            disabled={currentPage === totalPages}
            onClick={() => { fetchProducts(currentPage + 1); window.scrollTo({ top: 0, behavior: "smooth" }) }}
          >
            Próxima ›
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && products.length === 0 && (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>🔍</span>
          <h2>Nenhum produto encontrado</h2>
          <p>Tente ajustar os filtros ou volte em breve — novos cupons são adicionados todos os dias.</p>
          {hasActiveFilters && (
            <button className={styles.clearBtn} onClick={clearFilters}>
              Limpar filtros
            </button>
          )}
        </div>
      )}
    </div>
    </>
  )
}
