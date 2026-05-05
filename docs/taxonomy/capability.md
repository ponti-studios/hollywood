# Capability

A capability is a product-facing domain inside Nexus — audio, text, image, video. It is a bounded context, not the platform itself.

Currently `audio` is the only implemented capability, living in `src/nexus/audio/` with routes under `/v1/audio/`. Future capabilities like `text` and `image` would follow the same pattern: owning package, capability routes, domain-specific schema and workers.

Name the platform `nexus`. Name a domain `audio` or `text`. Do not name the platform after one of its capabilities.
