import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT if present
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

// Redirect to /login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const loginPath = import.meta.env.BASE_URL + 'login'
    if (err.response?.status === 401 && window.location.pathname !== loginPath) {
      sessionStorage.removeItem('token')
      window.location.href = loginPath
    }
    return Promise.reject(err)
  }
)

export const getSolicitations = (params = {}) =>
  api.get('/solicitations', { params }).then(r => r.data)

export const getSolicitation = (id) =>
  api.get(`/solicitations/${id}`).then(r => r.data)

export const getAlignment = (id, profileId) =>
  api.get(`/solicitations/${id}/alignment`, { params: { profile_id: profileId } }).then(r => r.data)

export const triggerAlignment = (id) =>
  api.post(`/solicitations/${id}/align`).then(r => r.data)

export const watchSolicitation = (id, watched) =>
  api.patch(`/solicitations/${id}/watch`, null, { params: { watched } }).then(r => r.data)

export const triggerScrape = (params = {}) =>
  api.post('/solicitations/scrape', params).then(r => r.data)

export const getScrapeStatus = () =>
  api.get('/solicitations/scrape/status').then(r => r.data)

export const getDashboard = () => {
  const isAdmin = sessionStorage.getItem('is_admin') === 'true'
  const profileId = isAdmin ? localStorage.getItem('adminProfileId') : null
  const params = profileId ? { profile_id: profileId } : {}
  return api.get('/dashboard', { params }).then(r => r.data)
}

export const getProfiles = () =>
  api.get('/profiles').then(r => r.data)

export const createProfile = (body) =>
  api.post('/profiles', body).then(r => r.data)

export const getCapabilities = (profileId) =>
  api.get('/capabilities', { params: { profile_id: profileId } }).then(r => r.data)

export const createCapability = (body) =>
  api.post('/capabilities', body).then(r => r.data)

export const updateCapability = (id, body) =>
  api.patch(`/capabilities/${id}`, body).then(r => r.data)

export const deleteCapability = (id) =>
  api.delete(`/capabilities/${id}`).then(r => r.data)

export const createProject = (body) =>
  api.post('/projects', body).then(r => r.data)

export const getProject = (id) =>
  api.get(`/projects/${id}`).then(r => r.data)

export const generateDraft = (projectId, sectionType, tone = 'technical', focusArea = 'balanced') =>
  api.post(`/projects/${projectId}/generate`, { section_type: sectionType, tone, focus_area: focusArea }).then(r => r.data)

export const getDrafts = (projectId) =>
  api.get(`/projects/${projectId}/drafts`).then(r => r.data)

export const updateDraft = (projectId, draftId, content) =>
  api.patch(`/projects/${projectId}/drafts/${draftId}`, { content }).then(r => r.data)

export const getDraftDiff = (projectId, draftId, againstId) =>
  api.get(`/projects/${projectId}/drafts/${draftId}/diff`, { params: { against: againstId } }).then(r => r.data)

export const triggerSamCsvImport = (params = {}) =>
  api.post('/solicitations/import/sam-csv', params).then(r => r.data)

export const getSamCsvImportStatus = () =>
  api.get('/solicitations/import/sam-csv/status').then(r => r.data)

export const triggerGrantsScrape = (params = {}) =>
  api.post('/solicitations/scrape/grants', params).then(r => r.data)

export const getGrantsScrapeStatus = () =>
  api.get('/solicitations/scrape/grants/status').then(r => r.data)

export const triggerSamScrape = (params = {}) =>
  api.post('/solicitations/scrape/sam', params).then(r => r.data)

export const getSamScrapeStatus = () =>
  api.get('/solicitations/scrape/sam/status').then(r => r.data)

export const triggerDodScrape = () =>
  api.post('/solicitations/scrape/dod').then(r => r.data)

export const getDodScrapeStatus = () =>
  api.get('/solicitations/scrape/dod/status').then(r => r.data)

export const runAlignment = (params = {}) =>
  api.post('/align/run', null, { params: { skip_scored: true, ...params } }).then(r => r.data)

export const getAlignStatus = () =>
  api.get('/align/status').then(r => r.data)

export const getKeywords = (activeOnly = false) =>
  api.get('/keywords', { params: { active_only: activeOnly } }).then(r => r.data)

export const createKeyword = (keyword) =>
  api.post('/keywords', { keyword }).then(r => r.data)

export const toggleKeyword = (id, active) =>
  api.patch(`/keywords/${id}`, null, { params: { active } }).then(r => r.data)

export const deleteKeyword = (id) =>
  api.delete(`/keywords/${id}`).then(r => r.data)

export const changePassword = (currentPassword, newPassword) =>
  api.patch('/auth/password', { current_password: currentPassword, new_password: newPassword }).then(r => r.data)

export const getMe = () =>
  api.get('/auth/me').then(r => r.data)

export const generateCapabilitiesFromUrl = (url) =>
  api.post('/capabilities/generate/url', { url }).then(r => r.data)

export const generateCapabilitiesFromFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/capabilities/generate/file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export default api
