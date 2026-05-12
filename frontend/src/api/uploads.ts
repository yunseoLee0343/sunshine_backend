import client from './client'

export async function uploadPlantImage(file: File): Promise<{ image_ref: string }> {
  const form = new FormData()
  form.append('file', file)

  const { data } = await client.post<{ image_ref: string }>(
    '/uploads/plant-image',
    form,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  )

  return data
}
