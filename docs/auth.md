# Authentication

JWT **access + refresh** tokens. Access tokens are short-lived bearer
credentials; refresh tokens are long-lived, rotated on every use, and
revocable via a DB table.

## Tokens

| | Access | Refresh |
|---|---|---|
| Format | JWT (HS256) | opaque `secrets.token_urlsafe(48)` |
| Claims | `sub`, `exp`, `iat`, `jti`, `type=access` | none — validated by hash lookup |
| Lifetime | `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30) | `REFRESH_TOKEN_EXPIRE_DAYS` (default 14) |
| Storage | client `localStorage` | client `localStorage`; server stores **only** `sha256(token)` in `refresh_tokens` |
| Sent as | `Authorization: Bearer <token>` | request body to `/auth/refresh` and `/auth/logout` |

`decode_access_token` rejects any JWT whose `type` is not `access`, so a
refresh token presented as a bearer is a 401.

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password, full_name?}` | `TokenPair` (201) |
| POST | `/api/auth/login` | `{email, password}` | `TokenPair` |
| POST | `/api/auth/refresh` | `{refresh_token}` | `TokenPair` (rotated) |
| POST | `/api/auth/logout` | `{refresh_token}` | 204 |
| GET  | `/api/auth/me` | — | `UserOut` |

`TokenPair` = `{access_token, refresh_token, token_type, expires_in, user}`.

## Rotation & reuse detection

`/auth/refresh`:

1. Look up `sha256(presented_token)` in `refresh_tokens`.
2. Not found → 401.
3. **Already revoked** → treat as compromise: revoke every non-revoked
   token for that `user_id`, return 401. (A legitimate client's next
   refresh will now also fail, forcing a fresh login — the intended
   safety response.)
4. Expired → 401.
5. Otherwise: mark the row `revoked`, issue a brand-new pair.

`login` also prunes: deletes expired rows, then revokes all but the newest
10 live tokens per user.

## Client behaviour (`frontend/src/lib/api.ts`)

The axios response interceptor catches a `401` on any non-`/auth/` call,
runs a single refresh (de-duplicated across concurrent 401s via a shared
promise), retries the original request with the new access token, and
redirects to `/login` if the refresh fails.

## Tests

`backend/tests/test_auth_refresh.py` — rotation, old-token rejection,
reuse-detection cascade, logout revocation, refresh-as-bearer rejection,
unknown-token rejection.
