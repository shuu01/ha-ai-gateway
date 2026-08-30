## Purpose

Provides the shared provider pool for AI Gateway: user-configured upstream providers as config subentries, a weighted failover router, and per-provider health tracking with cooldowns. Conversation and TTS platforms reuse it later.

## ADDED Requirements

### Requirement: Configure providers as subentries
Users SHALL be able to add, reconfigure, and delete provider subentries on the single AI Gateway config entry. Each provider SHALL carry a provider type, endpoint URL, optional API key, model, and an integer weight. Editing provider configuration SHALL take effect without manually reloading the integration.

#### Scenario: Add a provider
- **WHEN** the user adds a new provider subentry with a type, endpoint, API key, model, and weight
- **THEN** the provider appears in the pool and participates in routing

#### Scenario: Reconfigure a provider
- **WHEN** the user changes an existing provider's model or weight
- **THEN** routing uses the updated settings for subsequent requests

#### Scenario: Delete a provider
- **WHEN** the user deletes a provider subentry
- **THEN** the provider no longer participates in routing

### Requirement: Weighted failover routing
The router SHALL consider only providers that are enabled, currently healthy, and capable of serving the request (matching requested language and audio format). Candidates SHALL be tried in descending weight order; on equal weights the earlier-configured provider wins. The first successful response SHALL be returned; if every candidate fails, the request SHALL be reported as failed.

#### Scenario: Route to highest-weight provider
- **WHEN** two capable, healthy providers are configured with weights 3 and 1
- **THEN** the weight-3 provider is tried first

#### Scenario: Equal weights use configuration order
- **WHEN** two providers have the same weight
- **THEN** the provider configured first is tried first

#### Scenario: Skip incapable provider
- **WHEN** a request language is not supported by the highest-weight provider but is supported by a lower-weight provider
- **THEN** the higher-weight provider is skipped and the lower-weight provider is tried

#### Scenario: Failover on provider error
- **WHEN** the highest-weight provider fails and a lower-weight provider succeeds
- **THEN** the lower-weight provider's result is returned

#### Scenario: All providers fail
- **WHEN** every candidate provider fails
- **THEN** the request fails and the last error is recorded for diagnostics

### Requirement: Provider health and cooldowns
After a provider fails, it SHALL be excluded from routing for a duration that depends on the error type: timeout 120 seconds, connection/network 300 seconds, server (5xx) 300 seconds, invalid response 300 seconds, rate limit 1 hour, quota 1 hour. Authentication and configuration failures (e.g. HTTP 404) SHALL exclude the provider until it is reconfigured or the integration restarts. A successful request SHALL clear the provider's failure state. Failure of one provider SHALL NOT affect other providers or the gateway itself.

#### Scenario: Timeout triggers cooldown
- **WHEN** a provider times out on a request
- **THEN** the provider is not considered for routing for at least 120 seconds

#### Scenario: Rate limit triggers cooldown
- **WHEN** a provider returns a rate-limit error
- **THEN** the provider is not considered for routing for at least 1 hour

#### Scenario: Success clears failure state
- **WHEN** a provider succeeds after a previous failure
- **THEN** its failure state is cleared and it is fully eligible again

#### Scenario: Authentication disables provider
- **WHEN** a provider fails authentication
- **THEN** it is not considered for routing again until reconfigured or restarted, while other providers keep working

#### Scenario: Config error (404) disables provider
- **WHEN** a provider returns HTTP 404 (e.g. wrong base URL or unknown model)
- **THEN** it is classified as a configuration failure, is not considered for routing again until reconfigured or restarted, and the error message identifies the likely misconfiguration

### Requirement: Error classification
Provider failures SHALL be classified so that permanent failures (authentication, quota, configuration) are distinguished from transient ones (timeout, connection, rate limit, server, invalid response). A quota error SHALL be recognized both from HTTP 402 and from a 429 response carrying an `insufficient_quota` marker. A 404 SHALL be classified as a configuration failure with an actionable message.

#### Scenario: Quota detection from 429
- **WHEN** an upstream returns HTTP 429 with an `insufficient_quota` body marker
- **THEN** it is treated as a quota failure, not a rate limit

### Requirement: Routing diagnostics
The gateway SHALL expose which provider served the last request and, on failure, which provider errored and with what message.

#### Scenario: Successful request diagnostics
- **WHEN** a request succeeds via a given provider
- **THEN** the last-served provider is reported on the entity

#### Scenario: Failed request diagnostics
- **WHEN** all providers fail
- **THEN** the last error and its provider are reported on the entity
