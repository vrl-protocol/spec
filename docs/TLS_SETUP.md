# TLS Setup for PostgreSQL — Verifiable Reality Layer

## Current gap
The local live-validation run used `ssl = off` on the PostgreSQL server.
`VRL_DB_REQUIRE_TLS` defaults to `true` in the application; the DB side must
match.  All production traffic **must** be encrypted in transit.

---

## Step 1 — Generate a self-signed certificate (local / dev)

```powershell
# Run from the PostgreSQL data directory (e.g. C:\Program Files\PostgreSQL\17\data)
$DataDir = "C:\Program Files\PostgreSQL\17\data"

# Generate 4096-bit RSA key + self-signed cert valid 825 days
openssl req -new -x509 -days 825 -nodes `
    -keyout "$DataDir\server.key" `
    -out "$DataDir\server.crt" `
    -subj "/CN=localhost"

# PostgreSQL requires the key to be owner-readable only
icacls "$DataDir\server.key" /inheritance:r /grant:r "NT AUTHORITY\NetworkService:(R)"
```

For production use a certificate signed by a trusted CA (Let's Encrypt,
internal PKI, or a managed cloud certificate).

---

## Step 2 — Enable SSL in postgresql.conf

```ini
# C:\Program Files\PostgreSQL\17\data\postgresql.conf

ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file  = 'server.key'
# ssl_ca_file = 'root.crt'   # uncomment to require client certificates
```

Restart PostgreSQL after changing these settings:

```powershell
Restart-Service postgresql-x64-17
```

---

## Step 3 — Enforce SSL in pg_hba.conf

Replace `host` entries with `hostssl` to reject unencrypted connections:

```
# pg_hba.conf — enforce TLS for vrl_writer and vrl_reader
hostssl  verifiable_reality_layer  vrl_writer  127.0.0.1/32  scram-sha-256
hostssl  verifiable_reality_layer  vrl_reader  127.0.0.1/32  scram-sha-256
```

Reload after editing:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" reload -D "C:\Program Files\PostgreSQL\17\data"
```

---

## Step 4 — Configure the application

```powershell
# Require TLS (default; shown for clarity)
$env:VRL_DB_REQUIRE_TLS = "true"

# Point at the CA cert if using a custom CA (optional for self-signed + loopback)
# $env:VRL_DB_SSL_CA = "C:\path\to\root.crt"

$env:VRL_DATABASE_URL = "postgresql://vrl_writer:pw@localhost:5432/verifiable_reality_layer"
```

The `_ssl_context()` function in `app/db/connection.py` creates an
`ssl.SSLContext` with `Purpose.SERVER_AUTH` and `check_hostname = True`.
For a self-signed certificate on localhost you will need to either:

- Add the self-signed cert to the system trust store, **or**
- Set `VRL_DB_REQUIRE_TLS=false` **only** for local development (never production).

---

## Step 5 — Verify the connection is encrypted

```sql
SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid();
```

Expected: `ssl = true`, a valid cipher (e.g. `TLS_AES_256_GCM_SHA384`).

---

## Latency impact of TLS

TLS adds a one-time handshake cost per new connection (~1–3 ms on loopback).
Because the application uses a connection pool (`VRL_DB_MAX_POOL_SIZE=20`),
connections are reused across requests.  The steady-state per-request TLS
overhead is **zero** (TLS record encryption is handled by the kernel and is
negligible for the payload sizes used here).

The previous `ssl=off` configuration was a local validation shortcut only
and is not acceptable for any deployment that handles real trade data.
