# Release 0.1.1

Released: 2026-10-30

First tagged release. From now on HACS shows Silpo updates by version instead of commit hash.

## 🐛 Bug Fixes

- Re-authentication no longer sends an SMS on its own. Home Assistant recreates the reauth flow on every restart or failed setup, and each time it sent a new SMS code. The SMS is now sent only after you press **Submit** in the re-login dialog

## 🔧 Other Changes

- CI (unit + E2E tests, hassfest, HACS validation) and an automatic Release workflow
- `scripts/bump_version.py` for version bumps and releases

## 🔄 Update Instructions

1. Update via HACS or manually pull the latest version
2. Restart Home Assistant
3. If Silpo asks to log in again: Settings → Devices & services → Silpo → Reconfigure → Submit, then enter the SMS code
