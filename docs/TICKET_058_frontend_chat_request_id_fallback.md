# Claude Code Ticket: TICKET-058

## Goal
Fix Chat page request submission on non-HTTPS public dev origins by replacing direct `crypto.randomUUID()` usage with a safe request-id generator fallback.

## Root cause
The Chat page shows:

```text
답변을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
```

This message is emitted by `frontend/src/pages/Chat/index.tsx` when `sendChat()` rejects.

Current `frontend/src/api/chat.ts` builds the request body with:

```ts
request_id: crypto.randomUUID(),
```

On a public HTTP dev origin such as:

```text
http://3.27.242.176:5173
```

`crypto.randomUUID()` may be unavailable or blocked because browser Web Crypto UUID generation is not reliably exposed outside secure contexts. If it throws before `axios.post()` executes, the frontend catch block displays the yellow error banner and the backend receives no request.

Backend direct API verification succeeded:

```text
POST http://localhost:8000/plants/{plant_id}/chat
-> 201 Created
```

So the immediate failure is not the backend Chat API contract. The frontend can fail before sending the request.

## Scope
Implement a frontend-only request id fallback.

This ticket owns:
- Chat request UUID generation
- frontend non-HTTPS dev compatibility
- `sendChat()` unit tests

This ticket does not own:
- backend Chat API changes
- Qwen/vLLM/LLMPort changes
- DB migration/seed changes
- Vite proxy redesign
- production HTTPS setup

## Current source
Current `frontend/src/api/chat.ts`:

```ts
import client, { DEMO_USER_ID } from './client'
import type { ChatAnswerResponse } from './types'

export async function sendChat(
  plantId: string,
  question: string,
): Promise<ChatAnswerResponse> {
  const { data } = await client.post<ChatAnswerResponse>(
    `/plants/${plantId}/chat`,
    {
      request_id: crypto.randomUUID(),
      user_id: DEMO_USER_ID,
      question,
    },
  )
  return data
}
```

## Required behavior

### 1. Do not call `crypto.randomUUID()` directly in request body
Replace direct usage with a helper:

```ts
request_id: createRequestId()
```

### 2. Prefer native `crypto.randomUUID()` when available
Use native browser UUID generation when it exists.

### 3. Provide fallback for non-secure dev contexts
If `globalThis.crypto?.randomUUID` is missing or not a function, generate an RFC4122-style UUID string in frontend code.

### 4. Always send a valid non-empty UUID string
`request_id` must never be:

```text
undefined
null
""
```

### 5. Preserve existing API contract
Do not change endpoint path or request body fields:

```text
POST /api/v1/plants/{plantId}/chat
body:
  request_id
  user_id
  question
```

## Implementation guide

Target file:

```text
frontend/src/api/chat.ts
```

Replace with:

```ts
import client, { DEMO_USER_ID } from './client'
import type { ChatAnswerResponse } from './types'

export function createRequestId(): string {
  const randomUUID = globalThis.crypto?.randomUUID
  if (typeof randomUUID === 'function') {
    return randomUUID.call(globalThis.crypto)
  }

  // Fallback for non-HTTPS public dev origins where crypto.randomUUID
  // is unavailable. This is sufficient for client-side request idempotency.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16)
    const value = char === 'x' ? random : (random & 0x3) | 0x8
    return value.toString(16)
  })
}

export async function sendChat(
  plantId: string,
  question: string,
): Promise<ChatAnswerResponse> {
  const { data } = await client.post<ChatAnswerResponse>(
    `/plants/${plantId}/chat`,
    {
      request_id: createRequestId(),
      user_id: DEMO_USER_ID,
      question,
    },
  )
  return data
}
```

## Optional hardening
If preferred, add an extra guard:

```ts
const requestId = createRequestId()
if (!requestId) {
  throw new Error('failed to create chat request id')
}
```

But the fallback should already guarantee a non-empty string.

## Tests

Add or update:

```text
frontend/src/api/__tests__/chat.test.ts
```

### Required test cases

1. Native UUID path

```text
given globalThis.crypto.randomUUID exists
when sendChat() is called
then request body uses the native UUID value
```

2. Fallback path

```text
given globalThis.crypto.randomUUID is undefined
when sendChat() is called
then request body includes a UUID-shaped non-empty request_id
```

3. API path unchanged

```text
sendChat('plant-1', '물 언제 줘?')
calls client.post('/plants/plant-1/chat', body)
```

4. Body contract unchanged

```text
body has:
  request_id
  user_id
  question
```

5. Fallback UUID format

Use regex:

```ts
/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
```

## Example test skeleton

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createRequestId, sendChat } from '../chat'
import client, { DEMO_USER_ID } from '../client'

vi.mock('../client', () => ({
  default: { post: vi.fn() },
  DEMO_USER_ID: '7507fdac-da23-5956-a5a4-9239de655be0',
}))

const mockPost = client.post as ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.clearAllMocks()
})

describe('createRequestId', () => {
  it('uses crypto.randomUUID when available', () => {
    const originalCrypto = globalThis.crypto

    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: { randomUUID: () => '11111111-1111-4111-8111-111111111111' },
    })

    expect(createRequestId()).toBe('11111111-1111-4111-8111-111111111111')

    Object.defineProperty(globalThis, {
      configurable: true,
      value: originalCrypto,
    } as any)
  })

  it('falls back to UUID-shaped value when crypto.randomUUID is unavailable', () => {
    const originalCrypto = globalThis.crypto

    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: {},
    })

    expect(createRequestId()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    )

    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: originalCrypto,
    })
  })
})

describe('sendChat', () => {
  it('posts valid chat body', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        request_id: 'req',
        plant_id: 'plant-1',
        intent: 'watering_question',
        answer: { 결론: '', 근거: '', 행동: '', 주의: '' },
        guardrails_applied: [],
        prompt_hash: '',
        model_name: 'mock',
        input_tokens: 0,
        output_tokens: 0,
        from_cache: false,
        created_at: new Date().toISOString(),
        is_reference_only: false,
        diagnosis_allowed: true,
      },
    })

    await sendChat('plant-1', '물 언제 줘?')

    expect(mockPost).toHaveBeenCalledWith(
      '/plants/plant-1/chat',
      expect.objectContaining({
        user_id: DEMO_USER_ID,
        question: '물 언제 줘?',
        request_id: expect.any(String),
      }),
    )
  })
})
```

Note: adjust the crypto restore section if TypeScript complains. The implementation target is the source file, not this exact test skeleton.

## Manual verification

### 1. Browser console check
Open the app at:

```text
http://3.27.242.176:5173
```

In DevTools Console:

```js
crypto.randomUUID
```

If it is undefined or throws when called, this ticket should fix the UI request submission.

### 2. Network tab check
Before patch:

```text
Click chat submit
-> no POST /api/v1/plants/{plantId}/chat appears
-> yellow error banner appears
```

After patch:

```text
Click chat submit
-> POST /api/v1/plants/{plantId}/chat appears
-> status 201 or backend error visible
```

### 3. EC2 proxy smoke test
Use `python3`, not `python`, on Ubuntu:

```bash
export PLANT_ID="814646d9-9cbe-5723-aedf-e9a9b7531e1f"
export USER_ID="7507fdac-da23-5956-a5a4-9239de655be0"
export REQ_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

curl -i "http://localhost:5173/api/v1/plants/$PLANT_ID/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"request_id\": \"$REQ_ID\",
    \"user_id\": \"$USER_ID\",
    \"question\": \"물 언제 줘야 해?\"
  }"
```

Expected:

```text
HTTP/1.1 201 Created
```

## Acceptance criteria
- `npm run build` passes.
- `npm test` passes if frontend tests are configured.
- Chat submit works from `http://3.27.242.176:5173`.
- Browser Network tab shows `POST /api/v1/plants/{plantId}/chat`.
- Request body contains a valid non-empty UUID-shaped `request_id`.
- Backend receives the request.
- Yellow error banner is not shown for request-id generation failure.
- No backend files changed.
- No LLMPort/Qwen/vLLM changes.

## Do not implement
- production HTTPS
- auth redesign
- backend Chat API changes
- Qwen/vLLM registry changes
- RAG/prompt changes
- sensor/MQTT changes
- Home page changes
