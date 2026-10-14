# Python Social Auth Security

If you think you have identified a security issue with a Weblate project, **do
not open a public issue**.

To responsibly report a security issue, please navigate to the Security tab for
the repository and click “Report a vulnerability”:

- [social-auth-core](https://github.com/python-social-auth/social-core/security/advisories/new)
- [social-auth-app-django](https://github.com/python-social-auth/social-app-django/security/advisories/new)

Be sure to include as much detail as necessary in your report. As with
reporting normal issues, a minimal reproducible example will help the
maintainers address the issue faster.

## Threat models

The [social-auth-core threat model](https://github.com/python-social-auth/social-core/blob/master/THREAT_MODEL.md)
documents the core library's trust boundaries, claimed and disclaimed security
properties, downstream responsibilities, and vulnerability triage rules.

The [social-auth-app-django threat model](https://github.com/python-social-auth/social-app-django/blob/master/THREAT_MODEL.md)
documents the Django integration's corresponding security contract. This
security policy remains the reporting channel for findings that violate a
property claimed by either model.

## Supported versions

Only the latest release is guaranteed to receive security fixes.

## Vulnerability disclosure

The security advisory is typically published together with the release addressing the vulnerability.
