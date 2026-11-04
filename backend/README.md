# J.A.C.K. Local Backend

Local FastAPI service for the J.A.C.K. macOS app. The server binds only to `127.0.0.1` and stores user-entered memories in SQLite on this Mac.

## Requirements

Python 3.10 or newer. The project uses an isolated environment in `.venv`; no global Python packages are needed.

## First run

From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Start the backend:

```sh
.venv/bin/python -m app
```

The default address is `http://127.0.0.1:8000`. To stop it, press Ctrl+C.

## Verify the endpoints

```sh
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/info
```

Expected health response:

```json
{"status":"ok","app":"J.A.C.K.","service":"J.A.C.K. Local Backend","version":"0.1.0"}
```

The info response reports the service name, version, and available `health`, `info`, and `memories` modules.

## Local memory data model

On macOS, the SQLite database is created automatically at:

```text
~/Library/Application Support/J.A.C.K./memories.sqlite3
```

On other platforms, the default is `~/.local/share/J.A.C.K./memories.sqlite3`. No example memories are inserted. To use a different local path, set `JACK_MEMORY_DB_PATH` in `.env` to an absolute path before starting the backend.

The database uses schema version 2, tracked with SQLite `PRAGMA user_version`. Startup upgrades the existing database in place inside a transaction; it never deletes or replaces the database file. Before upgrading a database that has the old schema, the backend writes a private SQLite backup beside it:

```text
memories.sqlite3.pre-v2.bak
```

Both the database and backup use owner-only file permissions. If migration fails, SQLite rolls back the schema changes, keeps the original records, and retains the backup for inspection or manual recovery. The backend then fails startup rather than serving partially migrated data. Make a separate backup before upgrading if you want a copy outside the application support folder.

The old Italian categories are migrated as follows:

| Old value | Schema v2 |
| --- | --- |
| `personale` | `identity` |
| `lavoro` | `work` |
| `progetti` | `projects` |
| `preferenze` | `preferences` |
| `note` | `other` |

Each memory stores `id`, `title`, `content`, `category`, `source_type`, nullable `source`, `verification`, `tags`, `importance` (1–5), `excluded`, nullable `conversation_id`, nullable `last_used`, `created_at`, and `updated_at`. The source type is `saved`, `retrieved`, or `inference`; verification is `verified`, `to_verify`, or `inferred`.

Each `memory_links` row stores `id`, `from_id`, `to_id`, `relation`, `strength` (1–3), and `created_at`. The database also keeps an internal normalized relation key for duplicate detection; it is not returned by the API.

Existing IDs, titles, content, and timestamps are preserved. Historical records receive conservative metadata defaults: `source_type=saved`, `source=null`, `verification=to_verify`, empty `tags`, `importance=3`, `excluded=false`, and null `conversation_id` / `last_used`. A null source deliberately means the old record did not retain provenance. New writes that omit optional metadata use `source=user_entry` and the same conservative verification/importance defaults.

Memory categories are `identity`, `work`, `projects`, `people`, `technical`, `preferences`, `events`, and `other`. Old category strings remain accepted by the existing memory endpoints and are returned as their v2 values.

### Memory endpoints

- `GET /api/v1/memories` — list/search with optional `q`, `category`, and `excluded` filters.
- `GET /api/v1/memories/{id}` — fetch one memory.
- `POST /api/v1/memories` — create a memory.
- `PUT /api/v1/memories/{id}` — update its title, content, and category; omitted metadata is preserved for older clients.
- `DELETE /api/v1/memories/{id}` — delete a memory and cascade-delete its links.
- `PUT /api/v1/memories/{id}/exclusion` — set the explicit `excluded` flag.
- `PUT /api/v1/memories/{id}/last-used` — set `last_used` to the current UTC time when explicitly requested by an application function.
- `GET /api/v1/memories/graph` — return `{ "nodes": [...], "edges": [...] }`, with the list filters available.

### Memory link endpoints

- `GET /api/v1/memories/links` — list links, optionally filtered with `memory_id`.
- `GET /api/v1/memories/links/{id}` — fetch one link.
- `POST /api/v1/memories/links` — create a link.
- `PUT /api/v1/memories/links/{id}` — update its endpoints, relation, or strength.
- `DELETE /api/v1/memories/links/{id}` — delete a link.

Links reference existing memories with SQLite foreign keys and `ON DELETE CASCADE`. Self-links are rejected. Links are treated as undirected for duplicate detection: reversing the endpoints, or changing only the Unicode case/outer whitespace of the same relation label, is a duplicate and returns HTTP 409. Strength is restricted to 1–3. Missing endpoint memories return 404; invalid fields return 422. A private normalized relation key supports this unique index and is not exposed by the API.

The store belongs to the current operating-system user through the local application support path. This backend currently has no account or multi-user authentication layer; it does not expose another device's database or synchronize records. Memory content is not logged. There are no automatic memory/link suggestions, AI extraction, or real `JackCore` graph integration in this milestone.

Run the backend API and migration tests from this directory with:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Configuration

Copy `.env.example` to `.env` and edit the local values. The bind host is restricted to `127.0.0.1`, including when configured through `JACK_HOST`. Browser development requests are limited to the exact local origins listed in `JACK_CORS_ORIGINS`; methods are limited to the memory API methods and credentials are disabled. The native macOS app does not use browser CORS.

AI providers, credentials, voice, and Mac automation are not included. Memory content stays in the local SQLite database and is not sent to AI providers or synchronized to a cloud service.

