## Context

See proposal.md — Why. Current state that shapes the approach:

- `stt.py` is a mock that writes audio to `/config/test.wav`; `tts.py`/`conversation.py` are also mocks. The STT entity today duplicates `dr.DeviceInfo` instead of reusing `base.py`'s `AIGatewayBaseEntity`.
- `core/registry.py` (`ProviderRegistry`) and `core/router.py` (`Router`) are empty placeholder classes. `runtime.py` defines `AIGatewayRuntime` (registry + router per entry) but `__init__.py` sets `entry.runtime_data = None` and never uses it.
- Config flow is single-instance with no user-configurable settings; no subentries exist yet. `strings.json` and `translations/en.json` must stay in sync, and config-flow changes must keep all three files aligned.
- No tests/lint/CI; verification is manual. No pip `requirements` in `manifest.json` and we must not add any if avoidable.
- Reference implementations studied: `openai_conversation/stt.py` + `open_router` (HA core) and `sfortis/openai_tts` (custom). All confirmed: STT is buffer-then-upload, subentries are the modern multi-provider pattern, typed error→cooldown→health is proven.

## Goals / Non-Goals

**Goals:**
- A generic, platform-agnostic provider pool (subentries → registry → router) that STT uses now and conversation/TTS reuse later.
- Weighted failover (max-weight first, config-order tie-break) gated by capability and per-provider health.
- One exposed STT entity advertising union capabilities, routing through the pool.
- No new pip requirements.

**Non-Goals:**
- Gemini / Wyoming adapters (follow-up change).
- Conversation and TTS platforms (later changes; same `Router`).
- Weighted-random load balancing (weights are priority ordering only).
- Real streaming STT (OpenAI-compatible transcription is file-upload only).
- Per-provider health sensor entities (the health model is designed so a sensor can consume it later).

## Decisions

### D1: Providers are config subentries, one per provider
Each provider subentry carries its full identity — `{provider_type, endpoint, api_key, model, weight, prompt}` — because providers have independent credentials and endpoints (Groq key vs Gemini key vs keyless local). This differs from `openai_tts`, where the parent entry holds shared credentials; here the parent is just the gateway shell.

- Rationale: keeps the single-instance constraint intact while allowing an arbitrary number of providers, and gives each provider its own reconfigure flow. Matches the `openai_conversation`/`open_router`/`openai_tts` subentry pattern.
- Alternative rejected: one config entry per provider — breaks the "one gateway" concept and the router would live across entries.

### D2: Direct aiohttp engine, not the openai SDK
The `OpenAICompatibleProvider` posts multipart to `{endpoint}/audio/transcriptions` via HA's shared `async_get_clientsession` (pattern from `sfortis/openai_tts`). The `endpoint` value is the full OpenAI-compatible base **including** `/v1` (e.g. `https://api.openai.com/v1`, Groq `https://api.groq.com/openai/v1`, OpenRouter `https://openrouter.ai/api/v1`), matching the SDK/`open_router` convention; the provider appends only `/audio/transcriptions`.

- Rationale: one engine serves Groq, OpenRouter, Mistral, Ollama, LiteLLM, and self-hosted faster-whisper-server without pinning the `openai` package; supports per-endpoint quirks; keeps `manifest.json` `requirements` empty (aiohttp is a core HA dependency).
- Alternative rejected: `openai.AsyncClient(api_key, base_url)` — HA core's approach, but it pins a dependency and is less flexible for arbitrary backends.

### D3: One entity per platform, not per provider
`async_setup_entry` always creates a single `AIGatewaySTTEntity` per platform, even when the registry has zero STT providers. The entity is a stable "gateway" object: it is registered once and never recreated, so a single registration supports provider add/remove in place. When the pool is empty the entity is `unavailable` and advertises no language (rejecting all requests) rather than being hidden or advertising a fabricated language. This is the opposite of `openai_conversation`, which makes one entity per subentry.

### D4: In-place runtime rebuild, no reload
Because the entity is always registered, a provider change no longer needs a full entry reload. `async_setup_entry` subscribes to `SIGNAL_CONFIG_ENTRY_CHANGED` (`ConfigEntryChange.UPDATED`); on a subentry change it rebuilds the in-memory `ProviderRegistry` from `entry.subentries` in place, re-points the existing routers at the new registry, then calls `async_write_ha_state()` on the entity. `supported_languages` is already a live property reading the registry, so the advertised languages update automatically; an empty pool yields `[]` and the entity flips to `unavailable`. Rebuilding is idempotent, so no dedup guard is needed (unlike a full reload, where concurrent signals race).

### D5: Canonical audio contract
The entity advertises `WAV / PCM / 16-bit / 16 kHz / mono` (the Whisper-family floor) and re-wraps the raw PCM stream into a WAV container before upload (exactly what `openai_conversation/stt.py` does). HA resamples once to the advertised settings, so every adapter receives identical bytes and no per-provider transcoding is needed.

### D6: Router shape
`Router` is generic; platform operations are injected:

- `candidates(**capabilities)` → filter `enabled && health.available && supports(language, format)`, then stable-sort by `weight` descending (Python's `sorted` is stable, so subentry order is the tie-break).
- `run(op, *args, **kwargs)` → try each candidate in order, first success wins, `record_failure`/`record_success` on each attempt, raise `AllProvidersFailed` with per-provider errors. Used for STT (buffered).
- `run_stream(open_stream, ...)` → the streaming commit rule for future TTS/conversation: failover only until the first validated chunk; after that, committed. Not used in this change but the interface is reserved.

### D7: Error taxonomy and cooldown table
Typed exceptions mirroring `sfortis/openai_tts`, cooldowns per our design discussion:

| Error | Cooldown |
|---|---|
| timeout | 120s |
| connection / network | 300s |
| server (5xx) | 300s |
| invalid response (bad bytes / JSON-as-200) | 300s |
| rate limit (429) | 1h |
| quota (402 / 429 + `insufficient_quota`) | 1h |
| auth (401/403) | permanent — until reconfigure or restart |

Health is not persisted: on restart all providers start healthy ("available"). Cooldown fires at failure time; a success clears all state. Permanent auth failures disable only that provider — never the gateway.

### D8: Provide subentry flows for add/reconfigure
The config entry exposes subentry flows (add/reconfigure of an STT provider). Reconfigure ends with `async_update_reload_and_abort` (verified in HA core: `config_entries.py:3826`); add/delete fire `SIGNAL_CONFIG_ENTRY_CHANGED` (`ConfigEntryChange.UPDATED`) via `async_add_subentry`/`async_remove_subentry`. The runtime's in-place rebuild listener (D4) reacts to that dispatch to keep the pool current; no full reload is needed for provider add/reconfigure/delete.

### D9: Migration
Bump `VERSION` to 2 and support only v2 going forward: no `async_migrate_entry`. HA only invokes migration when the stored version differs from `VERSION`; without a handler, a stored v1 (mock-era) entry fails to load ("Migration handler not found", `config_entries.py:1174`) and is effectively dropped — the user removes and re-adds it. Mocks are throwaway, so there is no data worth preserving. New installs store version 2 and never touch the migration path (`config_entries.py:1152`).

### D10: Diagnostics
`last_provider` and `last_error` attributes on the STT entity, populated by the router result/exception. `last_error` carries the error message from the failed provider. `provider_count` exposes how many providers are registered, and `available` reflects whether the pool is non-empty — together these surface the empty-pool `unavailable` state rather than hiding it.

### D11: Buffer cap
`MAX_AUDIO_BUFFER_BYTES` ≈ 60s of 16 kHz 16-bit mono PCM (~1.9 MB). When the cap is hit, transcribe what was buffered rather than error. With `requires_external_vad=True` (the STT default we inherit), HA's VAD normally ends the stream; the cap is a safety net for stuck-mic/VAD-failure cases.

### D12: HTTP 404 is a permanent config failure, not a transient blip
A 404 from `{endpoint}/audio/transcriptions` is virtually always a configuration error — wrong base URL (missing `/v1`, e.g. `https://api.groq.com` instead of `https://api.groq.com/openai/v1`), a path the endpoint doesn't expose, or a model id that doesn't exist. It is not transient and does not self-heal, so it must not be treated as a 300s blip:

- **Add `ProviderConfigError(ProviderError)`** so a 404 has a distinct semantic type instead of collapsing to the generic base `ProviderError`.
- **Cooldown `None` (permanent disable), like auth** in the `COOLDOWNS` table. After one 404 the provider is skipped in `candidates()`, so subsequent requests fail over straight to a healthy provider (no recurring 404 round-trip every 5 minutes). Recovery is via reconfigure/restart, which rebuilds providers with fresh health — already covered by the in-place rebuild (D4) and the subentry flows (D8).
- **Actionable message** including the provider's body snippet: "HTTP 404: endpoint or model not found. Verify the base URL includes /v1 (e.g. https://api.groq.com/openai/v1) and the model id. Provider: {snippet}". This flows through `last_error`, the cooldown log, and `AllProvidersFailed`.
- Conservative alternative (rejected for v1): a long-but-non-permanent cooldown (e.g. 1h) to cover the rare case of a backend briefly 404ing during its own redeploy. 404 semantics do not self-heal, so permanent disable is preferred; 5xx stays transient.

## Risks / Trade-offs

- **Single 429 → 1h cooldown is aggressive** (a flapping backend is skipped for an hour) → the health model records consecutive failures, so an "N failures in 5 min" rule can be layered on later without structural change.
- **Union language advertising + skip-incapable routing** means a language no provider supports yields an error → acceptable; documented as ERROR result with `last_error`.
- **Buffered upload latency** (STT is not streaming) → inherent to the protocol; failover is cheap because the buffered bytes are simply re-sent.
- **Empty-pool entity is `unavailable`** → the gateway is always visible but inert until a provider is added; `provider_count`/`last_error` attributes guide the user. No fabricated language is advertised, so no silent-routing trap.
- **Cap truncates utterances longer than ~60s** → transcribe-what-we-have, still returns a result.
- **No SDK-managed retries** (direct aiohttp) → the router's failover is the retry mechanism; one attempt per provider, cooldown on failure.

## Migration Plan

1. Bump `VERSION` to 2; support only v2, no `async_migrate_entry` (D9).
2. Deploy/verify: install the component in HA; any existing v1 entry is dropped (remove and re-add), subentry flows add providers, entity appears, routing works.
3. Rollback: revert the change; mocks were throwaway so no user data depends on them.

## Open Questions

- **Test-connection button** in the provider subentry flow (e.g. a "verify endpoint/key" step) — nice-to-have; deferrable without changing the spec.
- **Exact cap value** (60s vs 120s of audio) — constant in one place; trivially adjusted later.
- **Multi-platform providers** (e.g. one OpenAI endpoint serving STT + conversation + TTS) — resolved: v1 ships STT-only subentries (subentry type `stt`); conversation/TTS each get their own subentry types in later changes.
