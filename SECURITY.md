# Security policy

Please report vulnerabilities privately through GitHub's **Security → Report a vulnerability** form on this repository rather than a public issue.

Things to keep in mind when using this integration:

- The **webhook URL is a secret.** Anyone who has it can trigger a refresh (not read data). Regenerate it by removing and re-adding the entry if it leaks.
- ICS "secret address" URLs and CalDAV passwords are stored in Home Assistant's config entry storage, like other integrations. Use app-specific passwords where your provider offers them.
- Diagnostics redact URLs, usernames, passwords and the webhook id.
