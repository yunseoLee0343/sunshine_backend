# Claude Code Ticket: TICKET-056

## Goal
Fix the frontend Home page crash caused by `plants.length` being evaluated when `plants` becomes `undefined`.

## Root cause
The current Home page assumes `fetchHome()` always returns an object with a valid `plants` array.

Current frontend code:

```tsx
const [plants, setPlants] = useState<PlantHomeCard[]>([])

useEffect(() => {
  fetchHome()
    .then((res) => setPlants(res.plants))
    .catch(() => setError('식물 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'))
    .finally(() => setLoading(false))
}, [])

...

if (plants.length === 0) {
  ...
}
```

Failure observed:

```text
Cannot read properties of undefined (reading 'length')
at Home index.tsx
```

This happens when `res.plants` is `undefined`, so `setPlants(undefined)` breaks the state invariant.

Additional context:
- `frontend/src/api/client.ts` uses `baseURL: '/api/v1'` and sends `X-User-Id`.
- `frontend/vite.config.ts` proxies `/api/v1` to backend root and strips the prefix.
- Backend `/home` supports user identity from `X-User-Id` or `?user_id=`.
- Manual curl without `X-User-Id` returns 422, while `/plants?user_id=...` returns `{ "plants": [...] }`.

## Scope
Implement a defensive Home data loading fix only.

This ticket owns:
- Home page plants state invariant
- `fetchHome()` response normalization
- frontend API fallback to `/plants`
- tests for `plants` never becoming undefined

This ticket does not own:
- backend endpoint redesign
- auth redesign
- new UI pages
- LLM/RAG/sensor changes
- production deployment

## Allowed files
- frontend/src/pages/Home/index.tsx
- frontend/src/api/home.ts
- frontend/src/api/types.ts only if type adjustment is required
- frontend/src/api/client.ts only if helper export is needed
- frontend/src/pages/Home/HomePlantCard.tsx only if required by type compatibility
- frontend/src/pages/Home/__tests__/*
- frontend/src/api/__tests__/*
- frontend/vite.config.ts only if proxy is missing or broken
- docs/TICKET_056.md

## Required behavior

### Home state invariant
`plants` must never be `undefined`.

Required pattern:

```tsx
const [plants, setPlants] = useState<PlantHomeCard[]>([])
```

Every state update must normalize unknown data into an array:

```tsx
setPlants(normalizeHomePlants(response))
```

### Response normalization
Add a small normalizer for Home response data.

Required logic:

```ts
function normalizeHomePlants(data: unknown): PlantHomeCard[] {
  const value = data as any

  if (Array.isArray(value)) return value
  if (Array.isArray(value?.plants)) return value.plants
  if (Array.isArray(value?.cards)) return value.cards
  if (Array.isArray(value?.items)) return value.items

  return []
}
```

Preferred location:
- `frontend/src/api/home.ts`, exported for tests.

### Fetch fallback
`fetchHome()` should remain the primary call.

If `/home` fails with 422 or returns no `plants` array, frontend should fall back to `/plants`.

Required behavior:

```text
try GET /home
  if valid plants array:
    return normalized HomeResponse
  else:
    fallback GET /plants
catch 422:
  fallback GET /plants
```

Reason:
- `/home` is the intended Home card API.
- `/plants?user_id=...` is confirmed working and returns `{ plants: [...] }`.
- Home page should not crash if `/home` contract drifts or returns validation error.

### Error handling
If both `/home` and `/plants` fail:
- set `plants` to `[]`
- set user-facing error
- do not throw during render

### Rendering
Render should use an array guaranteed by state.

Allowed:

```tsx
if (plants.length === 0) ...
plants.map(...)
```

Only if `plants` cannot become undefined.

Alternative defensive render is allowed:

```tsx
const safePlants = Array.isArray(plants) ? plants : []
```

Then use `safePlants.length` and `safePlants.map`.

## Implementation guide

### `frontend/src/api/home.ts`
Current code:

```ts
export async function fetchHome(): Promise<HomeResponse> {
  const { data } = await client.get<HomeResponse>('/home')
  return data
}
```

Replace with:

```ts
export function normalizeHomePlants(data: unknown): PlantHomeCard[] {
  const value = data as any
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.plants)) return value.plants
  if (Array.isArray(value?.cards)) return value.cards
  if (Array.isArray(value?.items)) return value.items
  return []
}

export async function fetchHome(): Promise<HomeResponse> {
  try {
    const { data } = await client.get<HomeResponse>('/home')
    const plants = normalizeHomePlants(data)
    if (plants.length > 0 || Array.isArray((data as any)?.plants)) {
      return {
        user_id: (data as any)?.user_id ?? DEMO_USER_ID,
        plants,
      }
    }
  } catch (err: any) {
    const status = err?.response?.status
    if (status !== 422) {
      // Continue fallback for any fetch failure, but preserve option to log.
      console.warn('[fetchHome] /home failed; falling back to /plants', err)
    }
  }

  const { data } = await client.get('/plants')
  return {
    user_id: (data as any)?.user_id ?? DEMO_USER_ID,
    plants: normalizeHomePlants(data),
  }
}
```

Notes:
- `client` already sends `X-User-Id`.
- Do not hardcode `?user_id=` unless needed.
- If `/plants` endpoint requires query param despite header, use `{ params: { user_id: DEMO_USER_ID } }`.

### `frontend/src/pages/Home/index.tsx`
Ensure `setPlants` receives only arrays:

```tsx
fetchHome()
  .then((res) => setPlants(Array.isArray(res.plants) ? res.plants : []))
  .catch((err) => {
    console.error('[Home] failed to load plants', err)
    setPlants([])
    setError('식물 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')
  })
  .finally(() => setLoading(false))
```

## Tests

Add tests for:

### Home page
- initial render does not throw.
- `{ plants: [...] }` response renders cards.
- `{ plants: undefined }` response renders empty state, not ErrorBoundary.
- `{ cards: [...] }` response renders cards.
- `/home` 422 and `/plants` success renders cards.
- `/home` failure and `/plants` failure renders error state without crashing.
- `plants.length` is never called on undefined.

### API normalizer
- `normalizeHomePlants({ plants: [x] }) -> [x]`
- `normalizeHomePlants({ cards: [x] }) -> [x]`
- `normalizeHomePlants({ items: [x] }) -> [x]`
- `normalizeHomePlants([x]) -> [x]`
- `normalizeHomePlants(undefined) -> []`
- `normalizeHomePlants({}) -> []`

### Proxy sanity
If frontend dev proxy is part of testable config:
- `/api/v1/home` is proxied to backend `/home`.
- `/api/v1/plants` is proxied to backend `/plants`.

## Manual verification

From EC2:

```bash
cd ~/sunshine_backend

curl -fsS "http://localhost:8000/plants?user_id=7507fdac-da23-5956-a5a4-9239de655be0" | jq .
```

Expected:

```json
{
  "plants": [
    {
      "plant_id": "814646d9-9cbe-5723-aedf-e9a9b7531e1f",
      "nickname": "초록이"
    }
  ]
}
```

Run frontend:

```bash
cd ~/sunshine_backend/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://54.206.46.42:5173
```

Expected:
- no ErrorBoundary page
- Home page either shows plant cards or controlled empty state
- console has no `Cannot read properties of undefined (reading 'length')`

## Acceptance criteria
- frontend builds with `npm run build`.
- Home page no longer crashes when `/home` returns malformed data or 422.
- Home page displays `초록이` using fallback `/plants` if `/home` fails.
- no backend files changed.
- no unrelated frontend routes changed.
- no hardcoded RunPod/vLLM changes.
- no LLM/RAG/sensor code touched.

## Do not implement
- backend `/home` redesign
- auth redesign
- new onboarding behavior
- production nginx
- CORS middleware
- LLMPort changes
- RunPod endpoint changes
- sensor/MQTT changes
