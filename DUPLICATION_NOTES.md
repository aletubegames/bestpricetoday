# Código Duplicado: backend/app vs hf_space/app

## Status: Parcialmente Sincronizado

### Arquivos com Divergências Conhecidas

| Arquivo | Backend | HuggingFace Space | Nota |
|---------|---------|-------------------|------|
| `admin.py` | ✅ Versão completa (JWT admin + key) | ⚠️ Versão simplificada (key only) | HF Space não suporta JWT admin |
| `affiliate.py` | ✅ Completo | ❓ Verificar | - |
| `search.py` | ✅ Completo | ❓ Verificar | - |
| `providers/lomadee.py` | ✅ Versão atual | ⚠️ Desatualizada | Sincronizar |

### Outros Arquivos
✅ **Sincronizados**: `auth.py`, `search.py`, `products.py`, `alerts.py`, e maioria dos providers

### Ações Recomendadas

1. **Curto prazo**: Sincronizar `providers/lomadee.py` (backend → hf_space)
2. **Médio prazo**: Extrair módulo `shared/` com código comum
3. **Longo prazo**: Unificar ou documentar intencionalmente divergências

### Como Sincronizar

```bash
# Copiar arquivo específico
cp backend/app/services/providers/lomadee.py hf_space/app/services/providers/

# Verificar diff completo
diff -u backend/app hf_space/app > duplication.diff
```

---
*Última atualização: 2026-05-22*
