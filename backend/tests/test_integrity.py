"""
test_integrity.py — Testes de integridade estrutural

Objetivo: impedir que padrões inaceitáveis entrem ou voltem à codebase:

1. Endpoint /conversions/test — expõe dados falsos no dashboard de produção.
2. Commission hardcoded — qualquer comissão fixa/flat inserida como verdadeira
   (ex: commission_rate = 4.0 ou commission_value = 12.75 sem origem real).
3. Claims de receita/comissão em respostas de API sem dado real de plataforma.

Esses testes são ESTRUTURAIS — não precisam de banco nem de rede.
Eles inspecionam o código-fonte e as rotas registradas diretamente.
"""
import ast
import importlib
import inspect
import os
import re
import pytest
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent / "app"
HF_ROOT = Path(__file__).parent.parent / "hf_deploy" / "app"

# ─── Helpers ─────────────────────────────────────────────────────────────────

def collect_py_sources(*roots: Path) -> list[Path]:
    """Retorna todos os .py abaixo das raízes, excluindo venv e __pycache__."""
    files = []
    for root in roots:
        for p in root.rglob("*.py"):
            parts = p.parts
            if any(x in parts for x in ("venv", ".venv", "__pycache__", ".venv312")):
                continue
            files.append(p)
    return files


def source_of(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─── 1. Endpoint /conversions/test não deve existir em produção ──────────────

class TestNoFakeConversionEndpoint:
    """
    O endpoint POST /conversions/test (ou similar) injeta conversões falsas
    diretamente no banco de produção. Não deve existir em nenhum router.
    """

    def _find_test_conversion_routes(self) -> list[str]:
        hits = []
        for path in collect_py_sources(BACKEND_ROOT, HF_ROOT):
            src = source_of(path)
            # Detecta @router.post / @router.get / @app.post apontando para rota de teste
            if re.search(
                r'@\w+\.(post|get|put|patch)\s*\(\s*["\'].*convers.*test',
                src, re.IGNORECASE
            ):
                hits.append(str(path))
            # Também detecta se a string de path contém "test" junto com "conversion"
            for match in re.finditer(
                r'@\w+\.(post|get|put|patch)\s*\(\s*["\']([^"\']+)["\']',
                src
            ):
                route = match.group(2)
                if "convers" in route and "test" in route:
                    hits.append(f"{path}:{route}")
        return hits

    def test_no_test_conversion_route_in_source(self):
        """Nenhum arquivo Python deve definir uma rota /conversions/test."""
        hits = self._find_test_conversion_routes()
        assert hits == [], (
            "Endpoint de conversão de teste encontrado no código-fonte. "
            "Remova antes de fazer merge:\n" + "\n".join(hits)
        )

    def test_router_does_not_register_test_conversion(self):
        """O FastAPI app não deve ter nenhuma rota cujo path contenha 'conversions/test'."""
        try:
            from app.main import app
        except Exception:
            pytest.skip("Não foi possível importar o app (requer banco)")

        test_routes = [
            r.path for r in app.routes
            if hasattr(r, "path") and "convers" in r.path and "test" in r.path
        ]
        assert test_routes == [], (
            "App registrou rota de conversão de teste: " + str(test_routes)
        )


# ─── 2. Sem comissão hardcoded / flat rate ───────────────────────────────────

class TestNoHardcodedCommission:
    """
    Comissões hardcoded (ex: commission_rate = 4.0, commission_value = 12.75)
    nos arquivos de lógica de negócio produzem dados falsos no dashboard.
    Os únicos valores de comissão aceitáveis são os vindos da resposta das APIs
    de afiliados (atribuídos a variáveis, não literais em construções de modelo).
    """

    # Arquivos onde comissões PODEM aparecer como literal (schemas, testes, config)
    ALLOWED_FILES = {
        "schemas.py", "config.py", "test_integrity.py",
        "test_api.py", "test_providers.py", "test_ranking.py",
        "test_integrations.py",
    }

    # Padrões suspeitos: atribuição de comissão com literal numérico
    SUSPICIOUS_PATTERNS = [
        # commission_rate = <número>  (exceto 0 e None)
        r"commission_rate\s*=\s*(?!None|0(?:\.0+)?\b|0,)[0-9]+(?:\.[0-9]+)?(?!\s*\*)",
        # commission_value = <número literal não-zero>
        r"commission_value\s*=\s*(?!None|0(?:\.0+)?\b)[0-9]+(?:\.[0-9]+)?(?!\s*[*(/])",
    ]

    def _scan(self) -> list[str]:
        hits = []
        for path in collect_py_sources(BACKEND_ROOT, HF_ROOT):
            if path.name in self.ALLOWED_FILES:
                continue
            src = source_of(path)
            for pattern in self.SUSPICIOUS_PATTERNS:
                for m in re.finditer(pattern, src):
                    line_no = src[: m.start()].count("\n") + 1
                    hits.append(f"{path}:{line_no}  →  {m.group(0).strip()}")
        return hits

    def test_no_hardcoded_commission_literals(self):
        """
        Nenhum arquivo de produção deve atribuir commission_rate ou commission_value
        com um literal numérico não-zero. Valores devem vir da resposta da API.
        """
        hits = self._scan()
        assert hits == [], (
            "Comissão hardcoded encontrada — esses valores poluem o dashboard "
            "com dados falsos:\n" + "\n".join(hits)
        )


# ─── 3. conversion_tracker não usa estimated flat rate ───────────────────────

class TestConversionTrackerUsesRealData:
    """
    O tracker deve usar comissão informada pela plataforma.
    Proibido: any flat/estimated rate aplicado como fallback silencioso
    (ex: * 0.04, * 0.08, DEFAULT_COMMISSION_RATE = ...).
    """

    TRACKER_PATH = BACKEND_ROOT / "integrations" / "conversion_tracker.py"

    def _get_source(self) -> str:
        if not self.TRACKER_PATH.exists():
            pytest.skip("conversion_tracker.py não encontrado")
        return self.TRACKER_PATH.read_text(encoding="utf-8")

    def test_no_flat_commission_multiplier(self):
        """
        Nenhuma linha deve conter um multiplicador de comissão plano
        (ex: total * 0.04, price * 0.08).
        """
        src = self._get_source()
        # Procura padrão: variável * 0.0X onde 0.0X é um flat rate
        matches = re.findall(
            r"\b\w+\s*\*\s*0\.[0-9]{1,4}\b",
            src
        )
        # Filtra falsos positivos (ex: threshold < 0.001, arredondamentos)
        suspicious = [m for m in matches if not any(
            safe in m for safe in ("0.001", "0.0001", "1000", "100")
        )]
        assert suspicious == [], (
            "Multiplicador de comissão flat encontrado em conversion_tracker.py:\n"
            + "\n".join(suspicious) + "\n"
            "Use o valor retornado pela API da plataforma."
        )

    def test_no_default_commission_constant(self):
        """Nenhuma constante DEFAULT_COMMISSION_RATE deve existir."""
        src = self._get_source()
        assert "DEFAULT_COMMISSION" not in src, (
            "Constante DEFAULT_COMMISSION encontrada em conversion_tracker.py. "
            "Comissões devem vir das plataformas."
        )

    def test_ml_commission_not_hardcoded(self):
        """
        No handler de webhook do Mercado Livre, commission_rate não deve ser
        atribuído com literal numérico (ex: commission_rate = 4.0).
        """
        src = self._get_source()
        # Procura especificamente: commission_rate = <número> dentro de handle_ml_webhook
        # Detecta ao nível de arquivo (conservador)
        m = re.search(r"commission_rate\s*=\s*(?!None)[0-9]+(?:\.[0-9]+)?\b", src)
        assert m is None, (
            f"commission_rate hardcoded encontrado em conversion_tracker.py: "
            f"'{m.group(0)}'. Use None quando a plataforma não retornar o valor."
        )


# ─── 4. Alertas e favoritos exigem owner_id ──────────────────────────────────

class TestOwnershipEnforcement:
    """
    Garante que os endpoints de alertas e favoritos rejeitam requisições
    sem owner_id — tanto no schema Pydantic quanto nas queries.
    """

    def test_alert_create_schema_requires_owner_id(self):
        """AlertCreate deve exigir owner_id (Field obrigatório, não Optional)."""
        from app.schemas.schemas import AlertCreate
        import pydantic

        # Tenta criar sem owner_id — deve lançar ValidationError
        with pytest.raises((pydantic.ValidationError, TypeError)):
            AlertCreate(query="notebook", target_price=3000.0)  # type: ignore

    def test_alert_create_schema_rejects_empty_owner(self):
        """AlertCreate com owner_id vazio deve falhar."""
        from app.schemas.schemas import AlertCreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            AlertCreate(query="notebook", target_price=3000.0, owner_id="")

    def test_favorite_create_schema_requires_owner_id(self):
        """FavoriteCreate deve exigir owner_id."""
        from app.schemas.schemas import FavoriteCreate
        import pydantic
        import uuid

        with pytest.raises((pydantic.ValidationError, TypeError)):
            FavoriteCreate(product_id=uuid.uuid4())  # type: ignore

    def test_alert_list_endpoint_requires_owner_id(self):
        """GET /alerts sem owner_id deve retornar 422 (parâmetro obrigatório)."""
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/alerts")

        resp = asyncio.run(run())
        assert resp.status_code == 422, (
            f"GET /alerts sem owner_id retornou {resp.status_code}, esperado 422. "
            "O endpoint está permitindo listagem global sem filtro de dono."
        )

    def test_alert_delete_endpoint_requires_owner_id(self):
        """DELETE /alerts/{id} sem owner_id deve retornar 422."""
        import asyncio
        import uuid
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.delete(f"/api/v1/alerts/{uuid.uuid4()}")

        resp = asyncio.run(run())
        assert resp.status_code == 422, (
            f"DELETE /alerts/{{id}} sem owner_id retornou {resp.status_code}, esperado 422."
        )

    def test_favorites_list_endpoint_requires_owner_id(self):
        """GET /favorites sem owner_id deve retornar 422."""
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.get("/api/v1/favorites")

        resp = asyncio.run(run())
        assert resp.status_code == 422

    def test_alert_create_body_requires_owner_id_field(self):
        """POST /alerts sem owner_id no body deve retornar 422."""
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                return await client.post("/api/v1/alerts", json={
                    "query": "notebook gamer",
                    "target_price": 3500.0,
                    # owner_id ausente
                })

        resp = asyncio.run(run())
        assert resp.status_code == 422, (
            f"POST /alerts sem owner_id retornou {resp.status_code}, esperado 422."
        )


# ─── 5. API base URL centralizada no frontend ────────────────────────────────

class TestFrontendApiCentralization:
    """
    Garante que nenhum arquivo do frontend declara NEXT_PUBLIC_API_URL
    com fallback inline (localhost ou produção hardcoded).
    A única fonte de verdade é src/lib/api.ts.
    """

    FRONTEND_SRC = Path(__file__).parent.parent.parent / "frontend" / "src"
    CANONICAL_FILE = "lib/api.ts"
    FORBIDDEN_PATTERN = re.compile(
        r'process\.env\.NEXT_PUBLIC_API_URL\s*\|\|'
    )

    def test_no_inline_api_url_fallback(self):
        if not self.FRONTEND_SRC.exists():
            pytest.skip("Diretório frontend/src não encontrado")

        violations = []
        for path in self.FRONTEND_SRC.rglob("*.ts"):
            if "node_modules" in str(path):
                continue
            if path.is_relative_to(self.FRONTEND_SRC) and str(path.relative_to(self.FRONTEND_SRC)) == self.CANONICAL_FILE:
                continue  # lib/api.ts é permitido ter o fallback
            src = path.read_text(encoding="utf-8")
            if self.FORBIDDEN_PATTERN.search(src):
                violations.append(str(path))

        for path in self.FRONTEND_SRC.rglob("*.tsx"):
            if "node_modules" in str(path):
                continue
            src = path.read_text(encoding="utf-8")
            if self.FORBIDDEN_PATTERN.search(src):
                violations.append(str(path))

        assert violations == [], (
            "Fallback de API URL encontrado fora de lib/api.ts:\n"
            + "\n".join(violations)
            + "\nImporte API_BASE de '@/lib/api' em vez de redeclarar o fallback."
        )

    def test_no_localhost_fallback_in_frontend(self):
        """Nenhum arquivo frontend deve ter fallback para localhost."""
        if not self.FRONTEND_SRC.exists():
            pytest.skip("Diretório frontend/src não encontrado")

        violations = []
        pattern = re.compile(r'localhost:[0-9]+')
        for ext in ("*.ts", "*.tsx"):
            for path in self.FRONTEND_SRC.rglob(ext):
                if "node_modules" in str(path):
                    continue
                src = path.read_text(encoding="utf-8")
                if pattern.search(src):
                    violations.append(str(path))

        assert violations == [], (
            "Fallback localhost encontrado no frontend:\n" + "\n".join(violations)
        )


# ─── 6. hf_deploy sincronizado com canônico ──────────────────────────────────

class TestHfDeploySynced:
    """
    Os endpoints alerts.py e favorites.py do hf_deploy devem ser idênticos
    aos do backend canônico. Divergência indica que sync_hf_deploy.sh
    não foi executado antes do deploy.
    """

    PAIRS = [
        ("app/api/v1/endpoints/alerts.py",    "hf_deploy/app/api/v1/endpoints/alerts.py"),
        ("app/api/v1/endpoints/favorites.py", "hf_deploy/app/api/v1/endpoints/favorites.py"),
        ("app/schemas/schemas.py",            "hf_deploy/app/schemas/schemas.py"),
    ]

    def test_hf_deploy_endpoints_in_sync(self):
        backend_root = Path(__file__).parent.parent
        diffs = []
        for canonical_rel, hf_rel in self.PAIRS:
            canonical = backend_root / canonical_rel
            hf = backend_root / hf_rel
            if not canonical.exists() or not hf.exists():
                continue
            if canonical.read_text() != hf.read_text():
                diffs.append(f"{hf_rel} difere de {canonical_rel}")
        assert diffs == [], (
            "hf_deploy está fora de sincronia com o backend canônico.\n"
            "Execute: ./backend/sync_hf_deploy.sh\n"
            + "\n".join(diffs)
        )
