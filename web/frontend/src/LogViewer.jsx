import { useState, useCallback, useEffect, useMemo } from 'react'
import './LogViewer.css'
import { IconBack } from './Icons'
import Button from './ui/Button'
import Badge from './ui/Badge'

const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'

function formatNum(n) {
  if (n == null || n === 0) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toLocaleString('zh-CN')
}

function StatCard({ label, value, icon, color }) {
  return (
    <div className="lv-stat-card" style={{ borderTopColor: color }}>
      <div className="lv-stat-card__icon" style={{ color, background: color + '15' }}>{icon}</div>
      <div className="lv-stat-card__label">{label}</div>
      <div className="lv-stat-card__value">{value}</div>
    </div>
  )
}

export default function LogViewer({ onBack }) {
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const fetchStats = useCallback(() => {
    setStatsLoading(true)
    fetch(`${API_BASE}/logs/stats`)
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => setStats(data))
      .catch(() => setStats(null))
      .finally(() => setStatsLoading(false))
  }, [])

  useEffect(() => { fetchStats() }, [fetchStats])

  const successRate = useMemo(() => {
    if (!stats || stats.total_conversions === 0) return '-'
    return ((stats.success_count / stats.total_conversions) * 100).toFixed(1) + '%'
  }, [stats])

  return (
    <div className="lv-manager">
      <header className="lv-header">
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          type="button"
        >
          <IconBack /> 返回转换
        </Button>
        <div className="lv-header__title">
          <h2>数据看板</h2>
        </div>
        <Badge variant="info" className="lv-header__badge">统计概览</Badge>
      </header>

      {/* ===== 统计卡片 ===== */}
      {statsLoading ? (
        <div className="lv-stats-loading">加载中…</div>
      ) : stats && stats.total_conversions > 0 ? (
        <section className="lv-stats-grid">
          <StatCard label="转换次数" value={formatNum(stats.total_conversions)} icon="📊" color="#3b82f6" />
          <StatCard label="成功率" value={successRate} icon="✅" color="#10b981" />
          <StatCard label="处理文件" value={formatNum(stats.total_files)} icon="📄" color="#8b5cf6" />
          <StatCard label="商品条目" value={formatNum(stats.total_items)} icon="📦" color="#f59e0b" />
          <StatCard label="覆盖门店" value={formatNum(stats.total_stores)} icon="🏪" color="#06b6d4" />
          <StatCard label="转换失败" value={formatNum(stats.error_count)} icon="❌" color="#ef4444" />
        </section>
      ) : (
        <div className="lv-empty">暂无数据记录</div>
      )}

      {/* ===== 模板使用统计 ===== */}
      {stats && stats.template_stats && stats.template_stats.length > 0 && (
        <section className="lv-tmpl-section">
          <h3 className="lv-tmpl-section__title">模板使用统计</h3>
          <div className="lv-tmpl-table-wrap">
            <table className="lv-tmpl-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>模板</th>
                  <th>转换次数</th>
                  <th>文件数</th>
                  <th>商品数</th>
                  <th>门店数</th>
                </tr>
              </thead>
              <tbody>
                {stats.template_stats.map((t, i) => (
                  <tr key={t.key} className="lv-tmpl-row">
                    <td className="lv-tmpl-index">{i + 1}</td>
                    <td className="lv-tmpl-name">{t.name}</td>
                    <td>{t.count}</td>
                    <td>{t.files}</td>
                    <td>{t.items}</td>
                    <td>{t.stores}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
