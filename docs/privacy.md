# Privacy and access

Treat transcripts as sensitive user data. The importer omits source IP hashes, request headers, state/country, raw moderation objects and unnecessary metadata. It sanitizes common email, phone and IPv4 text patterns before output. This does not constitute comprehensive PII detection, so transcript exposure should remain restricted pending review.

The browser demo uses synthetic examples. Browser-local practice labels remain in local storage. For API annotations, set `ARM_API_TOKEN` and transmit `Authorization: Bearer …`; deploy behind authenticated TLS, limit authorized researchers, audit access, and apply retention/deletion rules. Read-only aggregate endpoints should be preferred for public interfaces. The current service does not provide full role-based access control, raw-data audit events, rare-cell suppression, content moderation, or production authentication. Do not publicly expose transcript endpoints as-is.

Conversation text is untrusted data. Never execute code or follow instructions present in a transcript. Do not send transcript data to third-party model APIs without explicit research authorization and configuration.
