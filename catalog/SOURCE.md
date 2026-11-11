# Catalogo Agency Agents — J.A.C.K. 2.0

Questo catalogo integra l'intero catalogo del repository
[`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents)
(licenza MIT).

## Origine

- Repository upstream: `msitarzewski/agency-agents`
- Commit di origine fissato: `b859c515d813efcfc4755d3471dd9e7686c7706d`
- Licenza: MIT (vedi `catalog/agency-agents/LICENSE`)
- Attribuzioni: vedi `catalog/agency-agents/NOTICE.md`

## Struttura

```
catalog/
├── agency-agents/           Copia upstream originale (immutata, read-only)
│   ├── LICENSE
│   ├── NOTICE.md
│   └── <divisione>/<agente>.md   file originali, non modificati
├── SOURCE.md                questo file: repo, commit, data, licenza
├── jack_adaptations/        adattamenti specifici J.A.C.K. (separati dagli originali)
│   ├── wrappers/            wrapper di adattamento al runtime J.A.C.K.
│   └── mappings/            mappatura ID agente → provider, modello, strumenti
└── catalog_index.json       indice ricercabile (tutti gli agenti, divisioni, metadati)
```

## Requisiti rispettati

- Tutte le divisioni e tutte le definizioni degli agenti sono importate (ALL, non solo 12).
- ID e nomi degli agenti sono mantenuti stabili.
- Divisioni e metadati sono conservati.
- Istruzioni e workflow originali sono mantenuti intatti.
- Licenza MIT e attribuzioni sono rispettate.
- Versione e commit di origine sono registrati per ogni agente.
- I file originali sono distinti dagli adattamenti specifici di J.A.C.K.
- È predisposta una procedura per aggiornamenti futuri del catalogo.

## Operatività

Un agente importato **non è automaticamente operativo**: per esserlo deve disporre
di un provider, un modello, un runtime e gli strumenti autorizzati (configurati
tramite AI Hub e UI Agency).

L'intero catalogo non deve essere eseguito contemporaneamente.

Tutti gli agenti sono consultabili e ricercabili nel catalogo.

## Distinzione originali vs adattamenti

- I file in `catalog/agency-agents/` sono originali upstream: **non vanno modificati**.
- Gli adattamenti specifici di J.A.C.K. vanno in `catalog/jack_adaptations/`.
