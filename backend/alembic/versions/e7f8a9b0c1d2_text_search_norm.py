"""text search tolerante: unaccent + pg_trgm + bpt_norm/bpt_compact + índices GIN

Revision ID: e7f8a9b0c1d2
Revises: b9c8d7e6f5a4
Create Date: 2026-11-14 13:00:00.000000

Busca em affiliate_products.title passa a comparar em forma normalizada
(minúsculo, sem acento, não-alfanumérico → espaço) e compacta (sem espaços),
tolerando "airfryer"↔"Air Fryer", "eletrica"↔"Elétrica", "iphone15"↔"iPhone 15".
Índices trigram GIN cobrem LIKE %tok% e word_similarity (fallback de typo).
"""
from alembic import op


revision = "e7f8a9b0c1d2"
down_revision = "b9c8d7e6f5a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION bpt_norm(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS $$
            SELECT regexp_replace(
                lower(public.unaccent('public.unaccent'::regdictionary, $1)),
                '[^a-z0-9]+', ' ', 'g')
        $$
        """
    )
    # bpt_compact é auto-contida (sem chamar bpt_norm): função SQL IMMUTABLE
    # é inlineada na expressão do índice GIN e a chamada interna a bpt_norm
    # falhava na resolução durante o CREATE INDEX ("function bpt_norm(text)
    # does not exist"). Mesma semântica: bpt_norm sem espaços.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION bpt_compact(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS $$
            SELECT replace(
                regexp_replace(
                    lower(public.unaccent('public.unaccent'::regdictionary, $1)),
                    '[^a-z0-9]+', ' ', 'g'),
                ' ', '')
        $$
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ap_title_compact_trgm "
        "ON affiliate_products USING gin (bpt_compact(title) gin_trgm_ops);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ap_title_norm_trgm "
        "ON affiliate_products USING gin (bpt_norm(title) gin_trgm_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ap_title_norm_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_ap_title_compact_trgm;")
    op.execute("DROP FUNCTION IF EXISTS bpt_compact(text);")
    op.execute("DROP FUNCTION IF EXISTS bpt_norm(text);")
    # Extensões (unaccent, pg_trgm) NÃO são removidas no downgrade.
