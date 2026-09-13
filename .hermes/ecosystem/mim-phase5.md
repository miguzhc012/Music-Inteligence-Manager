# Phase 5: CLI Interface

## Visão Geral
Interface de linha de comando para interação com o MIM sem necessidade de UI web/desktop.

## Funcionalidades Planejadas

### Comandos Principais
```
mim play <query>          # Toca música com resolução automática
mim queue <query>         # Adiciona à fila
mim search <query>        # Busca na biblioteca
mim history               # Mostra histórico recente
mim stats                 # Estatísticas de escuta
mim recommendations       # Recomendações personalizadas
mim lyrics <query>        # Busca letras
```

### Interface
- Prompt interativo com autocomplete
- Suporte a comandos por voz (future)
- Modo scriptável (pipe)
- Integração com shell (bash/zsh completion)

### Stack
- Python `click` ou `typer` para CLI
- `rich` para output formatado
- `prompt_toolkit` para input avançado