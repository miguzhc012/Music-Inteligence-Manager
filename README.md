# MIM — Music Intelligence Manager

> Sistema pessoal de música orientado a Library, Metadata, Discovery, Playback, IA, dispositivos e múltiplas fontes.

## Visão Geral

O MIM é uma plataforma pessoal de música com o objetivo de permitir que o usuário ouça e gerencie sua música sem se preocupar com a complexidade interna do sistema.

**Princípio central:** *"I want to feel proud of it, but above all I want to be able to listen to my music easily regardless of where it is."*

## Arquitetura

```
MIM — MUSIC IA MANAGER
├── MCM (MIM Core)
│   ├── Domain: Identity, Version, Source, Release, Resolution, Playback, Lyrics, Materialization, History
│   ├── Ports: Repository interfaces e contratos
│   ├── Application: Services e resolvers
│   └── Infrastructure: SQLite repos, migrations, watcher
├── MCL (Mobile/Control Layer)
│   ├── Domain: Device, Session, Permission
│   └── Application: [Futuro]
└── Shared: Config, Logging, Events, DI
```

## Fase 3 - Consolidada

A Fase 3 foi completada com sucesso, implementando:

### Entidades de Domínio
- **Identity**: Obra musical abstrata (título + artista)
- **Version**: Variação específica da obra (normal, acoustic, live)
- **Source**: Origem concreta (local, remote, download)
- **Release**: Contexto de lançamento (álbum, single, EP)
- **ReleaseTrack**: Ocorrência de Version em Release
- **Resolution**: Resultado da resolução Version → Source com evidências
- **Confidence**: Score de confiança (0.0-1.0)
- **Availability**: Disponibilidade da source
- **Materialization**: Estado físico/lógico (cached, downloaded)
- **Playback**: Queue, estado, config, positions
- **Lyrics**: Letras sincronizadas e não-sincronizadas
- **History**: Eventos de playback e estatísticas de escuta

### Repositórios SQLite
- SQLiteIdentityRepository
- SQLiteVersionRepository
- SQLiteSourceRepository
- SQLiteLibraryEntryRepository
- SQLiteReleaseRepository
- SQLiteResolutionRepository
- SQLiteQueueRepository
- SQLitePlaybackStateRepository
- SQLiteLyricsRepository
- SQLiteMaterializationRepository
- SQLiteDeviceStorageRepository
- SQLiteHistoryRepository
- SQLitePlaySessionRepository

### Serviços de Aplicação
- **LibraryService**: Gerenciamento de library local
- **Scanner**: Escaneamento e reconciliação de arquivos
- **ResolutionService**: Resolução Version → Source com confidence
- **ResolverChain**: Chain local→cache→remote→download (custo zero primeiro)
- **ReleaseService**: CRUD de releases e tracks
- **PlaybackService**: Fila, repeat, shuffle, seek, volume
- **LyricsService**: Fetch/salvar letras (local/embedded/remote)
- **ResolutionApplicationService**: Orquestra resolução + materialização + playback

### Infraestrutura
- Migration runner automático (schema v1 a v7)
- DirectoryWatcher com watchdog
- Config management com dotenv
- Event bus para comunicação assíncrona

## Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Executar testes específicos
pytest tests/unit/application/test_playback_service.py -v
pytest tests/unit/infrastructure/test_lyrics_repository.py -v
pytest tests/integration/test_migrations.py -v
```

**Status: 71 testes passando**

## Execução

```bash
# Setup do virtualenv
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Executar app
python run_dev.py
```

## Próximas Fases (Planejadas)

- **Fase 4**: Discovery Engine - Busca por título/artista, busca acústica, ISRC match
- **Fase 5**: Recommendation Engine - Recomendações baseadas em histórico
- **Fase 6**: Provider Integration - Spotify, YouTube, Apple Music APIs
- **Fase 7**: Multi-device Sync - Sincronização entre dispositivos
- **Fase 8**: CLI/GUI - Interface para usuário final

## Status das Fases

```
FASE 1 ████████████████████ CONCLUÍDA
FASE 2 ████████████████████ ACEITA
FASE 3 ████████████████████ CONCLUÍDA
FASE 4 ░░░░░░░░░░░░░░░░░░░ PROJETO
```

## Contribuição

Este projeto segue TDD (Test-Driven Development) e DDD (Domain-Driven Design).

### Fluxo de desenvolvimento:
1. Definir entidade de domínio
2. Criar port/interface
3. Escrever teste que falha
4. Implementar infraestrutura
5. Implementar service
6. Adicionar teste de integração
7. Commit com mensagem Conventional Commits

### Mensagens de commit:
- `feat(domain): ...` - Nova entidade de domínio
- `feat(repo): ...` - Novo repositório
- `feat(application): ...` - Novo serviço de aplicação
- `feat(infra): ...` - Mudanças na infraestrutura
- `test: ...` - Adição de testes
- `refactor: ...` - Refatoração sem mudança de behavior

## Licença

MIT