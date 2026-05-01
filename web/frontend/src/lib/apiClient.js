import axios from 'axios'
import { normalizeApiError } from './errors'

// 与现有 App.jsx 保持一致（生产环境走反代前缀）。
export const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'
export const DOWNLOAD_BASE = import.meta.env.PROD ? '/wms/downloads' : '/downloads'

/**
 * 统一 axios 实例（复用项目已有 axios 依赖）。
 * - baseURL 仅负责 API 请求前缀
 * - 下载链接请使用 DOWNLOAD_BASE 直接拼接
 */
export const apiClient = axios.create({
  baseURL: API_BASE,
})

/**
 * 将 axios 请求错误归一化后抛出，方便调用方直接 catch 展示 message。
 *
 * 用法：
 *   try { await apiClient.get('/templates') } catch (e) { e.message }
 */
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const normalized = normalizeApiError(err)
    // 保留原始错误方便调试，同时提供一致的 message/status/data
    const out = new Error(normalized.message)
    out.status = normalized.status
    out.data = normalized.data
    out.codes = normalized.codes
    out.raw = normalized.raw
    return Promise.reject(out)
  }
)

