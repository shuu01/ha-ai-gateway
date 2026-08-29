## 1. Core provider plumbing

- [x] 1.1 Create `core/errors.py` with typed exception hierarchy: `ProviderError`, `ProviderAuthError`, `ProviderQuotaError`, `ProviderRateLimitError`, `ProviderServerError`, `ProviderNetworkError`, `ProviderTimeoutError`, `ProviderInvalidResponseError`, `AllProvidersFailed`
- [x] 1.2 Create `core/health.py` with `ProviderHealth`: `record_success()`, `record_failure(error)`, `available` property, cooldown table (timeout 120s, connection 300s, server 300s, invalid-response 300s, rate-limit 1h, quota 1h, auth permanent), non-persisted state

## 2. Provider adapter contract

- [x] 2.1 Create `core/provider.py` with abstract `Provider` base: identity (`unique_id`, `name`), routing knobs (`weight`, `enabled`), capabilities (`supported_languages`, `supported_formats`, `supports(language)`), and `async transcribe(metadata, audio)` raising typed errors
- [x] 2.2 Create `core/providers/openai_compatible.py` with `OpenAICompatibleProvider`: aiohttp multipart POST to `{endpoint}/v1/audio/transcriptions` via HA's shared session, HTTP-status → typed error classification (401/403 auth, 402 quota, 429 with `insufficient_quota` → quota, 429 → rate limit, 5xx → server, network → network), timeout handling, model + language + prompt fields
- [x] 2.3 Add `provider_factory(subentry, hass)` dispatch in `core/registry.py` (provider_type → adapter class; unknown type raises)

## 3. Registry and router

- [x] 3.1 Implement `core/registry.py` `ProviderRegistry`: `register()`, `providers(platform)`, `get(provider_id)`, `union_languages(platform)`
- [x] 3.2 Implement `core/router.py` `Router`: `candidates(**capabilities)` (filter enabled + available + `supports`, stable sort by weight desc) and `run(op, *args, **kwargs)` (try in order, record success/failure, raise `AllProvidersFailed` with per-provider errors); reserve `run_stream()` signature for streaming platforms
- [x] 3.3 Wire `runtime.py` `AIGatewayRuntime` to build the registry from entry subentries and expose a `Router` per platform

## 4. Config flow and provider subentries

- [x] 4.1 Add provider config constants to `const.py`: `CONF_PROVIDER_TYPE`, `CONF_ENDPOINT`, `CONF_API_KEY`, `CONF_MODEL`, `CONF_WEIGHT`, `CONF_PROMPT`, default endpoint, provider type values
- [x] 4.2 Bump `VERSION` to 2 in `config_flow.py`; support only v2 (no `async_migrate_entry` — v1 entries are dropped)
- [x] 4.3 Add STT provider subentry flow to `config_flow.py`: `async_get_supported_subentry_types`, `ConfigSubentryFlow` with add/reconfigure steps (provider type, endpoint, api_key optional, model, weight, prompt), ending with `async_update_reload_and_abort`
- [x] 4.4 Keep `strings.json` and `translations/en.json` in sync for all new subentry flow keys

## 5. Entity and platform wiring

- [x] 5.1 Update `__init__.py`: build `AIGatewayRuntime` from subentries, set `entry.runtime_data`, forward platform setups; subscribe to subentry changes and rebuild the in-memory registry (no full reload)
- [x] 5.2 Rewrite `stt.py`: always create one `AIGatewaySTTEntity`; advertise union languages + canonical contract (WAV/PCM/16-bit/16 kHz/mono); when the pool is empty the entity is `unavailable` and advertises no language; buffer stream with ~60s cap, re-wrap WAV, route via `router.run()` filtered by language; return `SpeechResult`
- [x] 5.3 Add `last_provider` and `last_error` attributes to the STT entity, populated from router results/exceptions
- [x] 5.4 Reuse `AIGatewayBaseEntity` device info in the STT entity (drop the duplicated `dr.DeviceInfo`)

## 6. Verification

- [ ] 6.1 Manual verification in HA: fresh install, add two providers with different weights, confirm max-weight-first routing and failover on error
- [ ] 6.2 Verify cooldown behavior: trigger timeout/connection/rate-limit errors and confirm providers are skipped for the configured durations, then recover
- [ ] 6.3 Verify version handling: a stored v1 (mock-era) entry fails to load and is dropped (remove + re-add); a v2 entry with no providers loads with an `unavailable` STT entity; adding a provider makes it available and adds its language
- [ ] 6.4 Verify strings: subentry flow renders correctly and `strings.json` == `translations/en.json`
