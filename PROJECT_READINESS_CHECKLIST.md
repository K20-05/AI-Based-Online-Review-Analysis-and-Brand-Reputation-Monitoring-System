# Project Readiness Checklist

Last updated: 2026-04-16

## 1) Production Security
- [x] `.env.example` documents strong `SECRET_KEY` and admin password expectations.
- [x] Startup now logs security warnings for risky config:
  - weak/default admin password
  - `SESSION_COOKIE_SECURE` disabled
  - localhost CORS origins enabled
- [ ] Production `.env` values rotated and verified on deployment target.
- [ ] Add rate limiting for auth endpoints.

## 2) API Performance and Caching
- [x] Dashboard review sample cache prewarm added at startup.
- [x] Dashboard review sample path uses memoized lookups for repeat filters.
- [x] API request latency logging added for all `/api/*` endpoints.
- [x] Slow endpoint warning logging added for:
  - `/api/dashboard/summary`
  - `/api/dashboard/trends`
  - `/api/dashboard/reviews`
- [ ] Track p95 latency over time (file/metrics sink + dashboard).

## 3) Testing and Regression Safety
- [x] CI workflow exists and runs test suite on push/PR.
- [ ] Add targeted tests for role authorization matrix on dashboard endpoints.
- [ ] Add tests for dashboard drilldown filters (`sentiment`, `brand`, `months`, `limit`).
- [ ] Add timeout/failure-path tests for dashboard API consumers.

## 4) Deployment Safety
- [x] `/api/health` endpoint exists.
- [ ] Add deployment health-check gate (fail deploy if health check fails).
- [ ] Pin and periodically audit dependency versions.
- [ ] Add container/runtime healthcheck in deployment manifest.

## 5) UX Reliability
- [x] Review sample loading path optimized to reduce repeated delays.
- [x] Frontend retry action added for review drilldown fetch failures.
- [x] Explicit timeout messaging added for drilldown fetch delays.

## Next Implementation Steps (Recommended Order)
1. Add role-access tests for dashboard routes.
2. Add drilldown filter and failure-path API tests.
3. Add p95 latency exporter for `/api/dashboard/*` endpoints.
4. Add deploy-time health check step in CI/CD.
