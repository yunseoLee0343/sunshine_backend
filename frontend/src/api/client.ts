import axios from 'axios'

// Deterministic demo UUID — mirrors app/seeds/demo_seed.py demo_id('user-001')
const DEMO_USER_ID = '7923c9bd-80d8-d2d1-1937-b9e0e7e28887'

const client = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': DEMO_USER_ID,
  },
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err?.response?.status
    if (status === 401) {
      window.location.replace('/')
    } else if (status === 403) {
      return Promise.reject(new Error('이 식물에 접근할 권한이 없어요.'))
    }
    return Promise.reject(err)
  },
)

export { DEMO_USER_ID }
export default client
