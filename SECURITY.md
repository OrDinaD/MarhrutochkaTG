# Security Policy

## Secret handling

This repository must not contain real credentials, bot tokens, API keys, private keys, service IDs, or local configuration files.

Use environment variables in a local `.env` file or in the hosting provider dashboard. The real `.env` file is intentionally ignored by Git.

## If a secret is exposed

1. Revoke or rotate the exposed value immediately in the provider dashboard.
2. Replace the committed value with a placeholder or remove it completely.
3. Check the repository history and hosted deployment settings.
4. Treat public repository history as already copied by scanners.

## Reporting

If you find a security issue in this repository, please contact the maintainer privately instead of opening a public issue with sensitive details.
