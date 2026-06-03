import { computed, ref } from "vue"
import { API_BASE_URL, readApiResponse } from "./api"

type AuthUser = {
  id: number
  username: string
  is_staff: boolean
  is_superuser: boolean
}

type AuthPayload = {
  authenticated: boolean
  user: AuthUser | null
  csrf_token?: string
  detail?: string
}

const user = ref<AuthUser | null>(null)
const csrfToken = ref("")
const loaded = ref(false)
const loading = ref(false)
let authStatusPromise: Promise<AuthUser | null> | null = null

export const currentUser = user
export const authLoaded = loaded
export const authLoading = loading
export const isAuthenticated = computed(() => Boolean(user.value))
export const isStaff = computed(() => Boolean(user.value?.is_staff || user.value?.is_superuser))

export async function fetchAuthStatus(force = false) {
  if (loaded.value && !force) return user.value
  if (authStatusPromise && !force) return authStatusPromise

  authStatusPromise = loadAuthStatus()

  return authStatusPromise
}

async function loadAuthStatus() {
  loading.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/auth/me/`, {
      credentials: "include",
    })
    const data = await readApiResponse(response, "Не удалось проверить вход") as AuthPayload

    applyAuthPayload(data)

    return user.value
  } finally {
    loaded.value = true
    loading.value = false
    authStatusPromise = null
  }
}

export async function login(username: string, password: string) {
  await ensureCsrfToken()

  const response = await fetch(`${API_BASE_URL}/auth/login/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken.value,
    },
    body: JSON.stringify({ username, password }),
  })
  const data = await readApiResponse(response, "Не удалось войти") as AuthPayload

  if (!response.ok) {
    throw new Error(data.detail || "Не удалось войти")
  }

  applyAuthPayload(data)
  loaded.value = true

  return user.value
}

export async function register(username: string, email: string, password: string, passwordConfirm: string) {
  await ensureCsrfToken()

  const response = await fetch(`${API_BASE_URL}/auth/register/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken.value,
    },
    body: JSON.stringify({
      username,
      email,
      password,
      password_confirm: passwordConfirm,
    }),
  })
  const data = await readApiResponse(response, "Не удалось зарегистрироваться") as AuthPayload

  if (!response.ok) {
    throw new Error(data.detail || "Не удалось зарегистрироваться")
  }

  applyAuthPayload(data)
  loaded.value = true

  return user.value
}

export async function logout() {
  await ensureCsrfToken()

  const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "X-CSRFToken": csrfToken.value,
    },
  })
  const data = await readApiResponse(response, "Не удалось выйти") as AuthPayload

  if (!response.ok) {
    throw new Error(data.detail || "Не удалось выйти")
  }

  applyAuthPayload(data)
  loaded.value = true
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const method = String(init.method || "GET").toUpperCase()
  const headers = new Headers(init.headers || {})

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    await ensureCsrfToken()
    headers.set("X-CSRFToken", csrfToken.value)
  }

  return fetch(input, {
    ...init,
    credentials: "include",
    headers,
  })
}

function applyAuthPayload(data: AuthPayload) {
  user.value = data.authenticated ? data.user : null

  if (data.csrf_token) {
    csrfToken.value = data.csrf_token
  }
}

async function ensureCsrfToken() {
  if (csrfToken.value) return

  await fetchAuthStatus(true)
}
