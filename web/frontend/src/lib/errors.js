/**
 * 将后端 / 网络 / axios 错误统一归一化，便于 UI 层展示。
 *
 * 不引入新依赖；兼容 axios 报错结构与 fetch 报错结构。
 *
 * @param {unknown} err
 * @param {{ fallbackMessage?: string }} [opts]
 * @returns {{
 *   message: string,
 *   status?: number,
 *   data?: any,
 *   codes?: any,
 *   raw: unknown,
 * }}
 */
export function normalizeApiError(err, opts = {}) {
  const fallbackMessage = opts.fallbackMessage || '请求失败'

  // 字符串/基础错误
  if (typeof err === 'string') return { message: err, raw: err }
  if (err instanceof Error && !('response' in err)) {
    return { message: err.message || fallbackMessage, raw: err }
  }

  /** @type {any} */
  const e = err

  // axios: err.response / err.request / err.code 等
  const status = e?.response?.status
  const data = e?.response?.data

  // FastAPI 常见：{ detail: ... } / { error: ... }
  let message =
    (typeof data === 'string' && data) ||
    data?.error ||
    data?.message ||
    (typeof data?.detail?.message === 'string' ? data.detail.message : '') ||
    (typeof data?.detail === 'string' ? data.detail : '') ||
    e?.message ||
    fallbackMessage

  // FastAPI validation errors: {detail: [{loc,msg,type}, ...]}
  if (!message && Array.isArray(data?.detail)) {
    message = data.detail.map(d => d?.msg).filter(Boolean).join('，') || fallbackMessage
  }

  // 某些业务错误会通过 detail 对象返回更多信息（如缺失 codes）
  const codes = data?.detail?.codes

  return {
    message,
    status,
    data,
    codes,
    raw: err,
  }
}
