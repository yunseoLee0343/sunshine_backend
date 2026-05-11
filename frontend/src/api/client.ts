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

export { DEMO_USER_ID }
export default client
