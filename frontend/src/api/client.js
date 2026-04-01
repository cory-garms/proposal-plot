import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export const getSolicitations = (params = {}) =>
  api.get('/solicitations', { params }).then(r => r.data)

export const getSolicitation = (id) =>
  api.get(`/solicitations/${id}`).then(r => r.data)

export const getAlignment = (id) =>
  api.get(`/solicitations/${id}/alignment`).then(r => r.data)

export const triggerScrape = (params = {}) =>
  api.post('/solicitations/scrape', params).then(r => r.data)

export const getScrapeStatus = () =>
  api.get('/solicitations/scrape/status').then(r => r.data)

export const getCapabilities = () =>
  api.get('/capabilities').then(r => r.data)

export const createProject = (body) =>
  api.post('/projects', body).then(r => r.data)

export const getProject = (id) =>
  api.get(`/projects/${id}`).then(r => r.data)

export const generateDraft = (projectId, sectionType) =>
  api.post(`/projects/${projectId}/generate`, { section_type: sectionType }).then(r => r.data)

export const getDrafts = (projectId) =>
  api.get(`/projects/${projectId}/drafts`).then(r => r.data)

export default api
