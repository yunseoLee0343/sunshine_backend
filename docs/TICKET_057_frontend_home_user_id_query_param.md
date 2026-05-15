# Claude Code Ticket: TICKET-057

## Goal
Fix Home page data loading after TICKET-056 by making frontend Home API calls explicitly pass `user_id` query params instead of relying only on the `X-User-Id` header.

## Root cause
TICKET-056 fixed the direct `plants.length` crash by normalizing `res.plants` before writing state. However, the runtime browser log still shows the Home page cannot load data:

```text
GET http://3.27.242.176:5173/api/v1/home 500
[fetchHome] /home failed; falling back to /plants
GET http://3.27.242.176:5173/api/v1/plants 500
[Home] failed to load plants AxiosError: Request failed with status code 500
```

Current `frontend/src/api/home.ts` still calls:

```ts
client.get<HomeResponse>('/home')
client.get('/plants')
```

These calls rely on `client.ts` sending `X-User-Id`. But manual EC2 verification confirmed that the query-param path works:

```bash
curl -fsS "http://localhost:8000/plants?user_id=7507fdac-da23-5956-a5a4-9239de655be0" | jq .
```

Therefore, the fallback is insufficient because it still does not use the confirmed-good `?user_id=...` path.

## Scope
Implement a minimal frontend-only patch.

This ticket owns:
- Home API user identity parameter hardening
- `/home` and `/plants` request params
- Home load regression tests

This ticket does not own:
- backend auth redesign
- backend `/home` or `/plants` behavior changes
- CORS or production nginx
- LLM/RAG/sensor work
- RunPod/vLLM integration

## Allowed files
- frontend/src/api/home.ts
- frontend/src/api/__tests__/home.test.ts
- frontend/src/pages/Home/__tests__/Home.test.tsx only if needed
- docs/TICKET_057.md

## Required behavior

### 1. `/home` request must include `user_id`
Change:

```ts
const { data } = await client.get<HomeResponse>('/home')
```

to:

```ts
const { data } = await client.get<HomeResponse>('/home', {
  params: { user_id: DEMO_USER_ID },
})
```

### 2. `/plants` fallback request must include `user_id`
Change:

```ts
const { data } = await client.get('/plants')
```

to:

```ts
const { data } = await client.get('/plants', {
  params: { user_id: DEMO_USER_ID },
})
```

### 3. Preserve TICKET-056 normalization
Do not remove `normalizeHomePlants`.

Continue to guarantee:

```text
fetchHome().then(res => Array.isArray(res.plants) === true)
```

### 4. Preserve `X-User-Id`
Do not remove the default `X-User-Id` header from `client.ts`.

This ticket adds query-param identity as an explicit compatibility path; it does not replace header-based identity globally.

## Implementation guide

Target file:

```text
frontend/src/api/home.ts
```

Replace current `fetchHome()` with:

```ts
export async function fetchHome(): Promise<HomeResponse> {
  try {
    const { data } = await client.get<HomeResponse>('/home', {
      params: { user_id: DEMO_USER_ID },
    })
    const plants = normalizeHomePlants(data)
    if (plants.length > 0 || Array.isArray((data as any)?.plants)) {
      return {
        user_id: (data as any)?.user_id ?? DEMO_USER_ID,
        plants,
      }
    }
  } catch (err) {
    console.warn('[fetchHome] /home failed; falling back to /plants', err)
  }

  const { data } = await client.get('/plants', {
    params: { user_id: DEMO_USER_ID },
  })

  return {
    user_id: (data as any)?.user_id ?? DEMO_USER_ID,
    plants: normalizeHomePlants(data),
  }
}
```

## Tests

Update `frontend/src/api/__tests__/home.test.ts`.

### Required test cases
- `fetchHome()` calls `/home` with `{ params: { user_id: DEMO_USER_ID } }`.
- When `/home` returns `{ plants: [...] }`, no fallback occurs.
- When `/home` returns 500, fallback calls `/plants` with `{ params: { user_id: DEMO_USER_ID } }`.
- When `/home` returns `{ plants: undefined }`, fallback calls `/plants` with query param.
- Result `plants` is always an array.
- If both `/home` and `/plants` fail, `fetchHome()` rejects and Home page catches it without crashing.

### Example assertion
```ts
expect(mockGet).toHaveBeenNthCalledWith(1, '/home', {
  params: { user_id: DEMO_USER_ID },
})

expect(mockGet).toHaveBeenNthCalledWith(2, '/plants', {
  params: { user_id: DEMO_USER_ID },
})
```

## Manual verification

From EC2 backend host:

```bash
cd ~/sunshine_backend

curl -i "http://localhost:8000/home?user_id=7507fdac-da23-5956-a5a4-9239de655be0"

curl -i "http://localhost:8000/plants?user_id=7507fdac-da23-5956-a5a4-9239de655be0"
```

Expected:
- `/plants?...` returns 200 with `{ "plants": [...] }`.
- `/home?...` should return 200 if backend home-card path is healthy; if not, frontend fallback still works.

Run frontend:

```bash
cd ~/sunshine_backend/frontend
npm run build
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://3.27.242.176:5173
```

Expected:
- no ErrorBoundary
- no `Cannot read properties of undefined (reading 'length')`
- no failed `/api/v1/plants` request caused by missing `user_id`
- Home page shows `초록이` if `/plants?...` returns the demo plant

## Acceptance criteria
- `npm run build` passes.
- `npm test` passes if frontend tests are configured.
- Browser console no longer shows `/api/v1/plants 500` caused by missing user identity.
- Home page either renders plant cards or controlled error state.
- `plants` state never becomes undefined.
- no backend files changed.
- no unrelated frontend files changed.

## Do not implement
- backend auth redesign
- backend `/home` redesign
- new API client abstraction
- CORS/nginx changes
- production deployment changes
- LLMPort/Qwen/vLLM changes
- sensor/MQTT changes
