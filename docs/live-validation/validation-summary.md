# Live Validation Summary

## Environment
- Database: `vrl_live_validation`
- PostgreSQL version: `17.9`
- WAL: `replica`
- synchronous_commit: `on`
- SSL: `off`

## Overall result
- Step 10: **PASS**
- Statement: `identical truth`

## Seed evidence hashes
- input hash: `ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7`
- output hash: `0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b`
- trace hash: `e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6`
- final proof: `7b58cd2c0b85716175e90136d025d8d282abb1b56cb98ffaa33d4cbde3db70a1`

## Step results
- Step 2 append-only enforcement: **PASS**
- Step 3 duplicate replay handling: **PASS**
- Step 4 audit chain validation: **PASS**
- Step 5 concurrency stress: **PASS**
- Step 6 latency measurement: **WARN**
- Step 7 replay validation: **PASS**
- Step 8 failure injection: **PASS**
- Step 9 adversarial input testing: **PASS**

## Latency snapshot
- request p95: `436.05ms`
- DB transaction p95: `233.54ms`
- lock wait p95: `24.03ms`

## Generated machine-readable reports
- `audit-chain-verification-report.json`
- `concurrency-integrity-report.json`
- `failure-test-report.json`
- `latency-report.json`
- `summary.json`

## Residual production gaps
- Transport TLS is not validated here because the local PostgreSQL server reported `ssl = off`.
- The audit-chain serialization lock preserves integrity, but current latency is above the target envelope and needs optimization before a stricter production SLA claim.
