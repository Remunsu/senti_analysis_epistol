export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api"

export async function readApiResponse(response: Response, fallbackMessage: string) {
  const contentType = response.headers.get("content-type") || ""

  if (contentType.includes("application/json")) {
    return response.json()
  }

  const text = await response.text()

  return {
    detail: text
      ? `${fallbackMessage}. Сервер вернул не JSON-ответ.`
      : fallbackMessage,
  }
}
