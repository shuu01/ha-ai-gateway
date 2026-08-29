## Purpose

The single speech-to-text entity AI Gateway exposes to Home Assistant: it presents the union of pool capabilities, accepts the canonical audio contract, buffers and re-wraps incoming PCM audio, and routes transcription through the provider pool.

## ADDED Requirements

### Requirement: Single STT entity for the pool
The gateway SHALL always create exactly one STT entity, regardless of provider count. When no STT provider is configured the entity SHALL remain registered but be `unavailable`, and SHALL not advertise any supported language.

#### Scenario: Providers configured
- **WHEN** one or more STT providers exist in the pool
- **THEN** exactly one STT entity is registered, available, and advertises the union of provider languages

#### Scenario: No providers configured
- **WHEN** no STT provider exists in the pool
- **THEN** exactly one STT entity is still registered but is `unavailable`, advertises no supported language, and rejects incoming audio

#### Scenario: Last provider removed
- **WHEN** the last STT provider is removed
- **THEN** the entity transitions to `unavailable` and stops advertising languages (it is not removed from the entity registry)

#### Scenario: Provider added after none
- **WHEN** the first STT provider is added to an empty pool
- **THEN** the entity transitions to available and advertises the new provider's languages (it is not recreated)

### Requirement: Advertise union of provider capabilities
The STT entity SHALL advertise the union of languages supported by its enabled STT providers. It SHALL advertise the canonical audio contract: WAV format, PCM codec, 16-bit, 16 kHz, mono.

#### Scenario: Language union
- **WHEN** two STT providers support different language sets
- **THEN** the entity advertises both sets combined

#### Scenario: Canonical audio contract
- **WHEN** Home Assistant queries the entity's supported audio settings
- **THEN** only WAV / PCM / 16-bit / 16 kHz / mono is advertised

### Requirement: Transcribe through the pool
The STT entity SHALL accumulate the incoming PCM audio stream, re-wrap it in a WAV container, and route it through the provider pool filtered by the requested language. On a successful transcription it SHALL return the text with success state; otherwise it SHALL return an error state.

#### Scenario: Successful transcription
- **WHEN** an audio stream is transcribed successfully by a provider
- **THEN** the entity returns the transcript text with a success state

#### Scenario: No provider succeeds
- **WHEN** the audio stream cannot be transcribed by any provider
- **THEN** the entity returns an error state with no text

#### Scenario: No provider configured
- **WHEN** audio is submitted while the pool has no providers
- **THEN** the entity rejects the request (error state, no text) without attempting transcription

### Requirement: Bounded audio buffering
The entity SHALL stop accumulating audio after a fixed safety cap (approximately 60 seconds of 16 kHz 16-bit mono PCM) and transcribe the buffered audio rather than buffer unboundedly.

#### Scenario: Stream exceeds the cap
- **WHEN** the incoming audio stream exceeds the safety cap without ending
- **THEN** the entity transcribes the buffered audio up to the cap
