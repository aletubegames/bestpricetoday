# 🎯 XPath Inspector - Extrator X

## O que é?
Ferramenta de desenvolvimento para capturar e inspecionar elementos DOM em páginas web, gerando automaticamente seletores XPath e JavaScript para automação.

## Como usar

### 1. Abrir a ferramenta
```javascript
// Cole no console do navegador (F12):
// Copie todo o conteúdo de extrator.js e cole no console
```

### 2. Interface visual
Um painel verde/vermelho aparecerá no canto inferior direito com:
- **▶ Ativar captura** - Inicia o modo de inspeção
- **Gerar JS final** - Exporta o código JavaScript
- **Limpar** - Reseta a captura

### 3. Inspecionar elementos
1. Clique em "▶ Ativar captura"
2. Clique nos elementos na página que deseja capturar
3. Renomeie os passos (clique no texto de nomear)
4. Observe os XPath gerados no painel

### 4. Gerar código
Clique em "Gerar JS final" para obter um script pronto para automação.

## Saída
- **Smart XPath** - Seletor otimizado
- **Full XPath** - Caminho completo do DOM
- **JavaScript pronto** - Código exportável

## Exemplo de uso
```javascript
// Capturar botão de login
// 1. Ativar captura
// 2. Clicar no botão
// 3. Renomear para "btnLogin"
// 4. Usar em scripts de automação
```

## Arquivos
- `extrator.js` - Script principal do inspetor

## Notas
- Funciona com qualquer site
- Gera XPath robusto e smart
- Ideal para criar scripts de web scraping
- Requer console do navegador (DevTools)
