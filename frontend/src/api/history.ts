import client from './client'
import type { CareLogItem, GrowthHistoryResponse, HistoryItem } from './types'

// Map a care log item to the unified HistoryItem shape
function careLogToHistoryItem(log: CareLogItem): HistoryItem {
  return {
    type: 'care_log',
    timestamp: log.acted_at,
    title: log.action_type === 'watering' ? '물주기' : '노트',
    summary: log.note ?? (log.action_type === 'watering' ? '물을 주었어요' : ''),
  }
}

export async function fetchHistory(plantId: string): Promise<HistoryItem[]> {
  // Try the dedicated history endpoint first; fall back to care-logs if missing
  try {
    const { data } = await client.get<GrowthHistoryResponse>(
      `/plants/${plantId}/history`,
    )
    // Backend returns newest-first; preserve that order
    return data.items
  } catch {
    // Endpoint not yet implemented — aggregate from care-logs
    const { data } = await client.get<{ plant_id: string; logs: CareLogItem[] }>(
      `/plants/${plantId}/care-logs`,
    )
    return data.logs.map(careLogToHistoryItem)
  }
}
