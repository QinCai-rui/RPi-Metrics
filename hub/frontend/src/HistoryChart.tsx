import { useEffect, useRef, useState } from 'react'
import type { History, Point } from './api'
import { rate, valueText } from './format'

const metrics = [
  { key: 'cpu_percent', label: 'CPU', unit: '%', ceiling: 100 },
  { key: 'ram_percent', label: 'RAM', unit: '%', ceiling: 100 },
  { key: 'swap_percent', label: 'Swap', unit: '%', ceiling: 100 },
  { key: 'disk_percent', label: 'Disk', unit: '%', ceiling: 100 },
  { key: 'temperature_celsius', label: 'Temperature', unit: ' °C', ceiling: 0 },
  { key: 'download_bytes_per_second', label: 'Download', unit: ' MiB/s', ceiling: 0 },
  { key: 'upload_bytes_per_second', label: 'Upload', unit: ' MiB/s', ceiling: 0 },
]

type Metric = typeof metrics[number]

function chartValue(value: number, metric: Metric) {
  return metric.unit === ' MiB/s' ? value / 1048576 : value
}

function Graph({ points, hours, metric, resolution }: {
  points: Point[]; hours: number; metric: Metric; resolution: History['resolution']
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const element = canvas.current!
    function draw() {
      const width = element.clientWidth
      const height = element.clientHeight
      const scale = window.devicePixelRatio || 1
      element.width = width * scale
      element.height = height * scale
      const ctx = element.getContext('2d')
      if (!ctx || width < 60) return
      ctx.scale(scale, scale)
      const end = Date.now()
      const start = end - hours * 3600000
      const left = 46
      const right = width - 12
      const top = 14
      const bottom = height - 25
      const numeric = points.flatMap(([, value]) => value == null ? [] : [chartValue(value, metric)])
      const max = Math.max(metric.ceiling, ...numeric, metric.unit === ' MiB/s' ? 0.1 : 1)
      const min = Math.min(0, ...numeric)
      ctx.font = '11px system-ui'
      ctx.fillStyle = '#486269'
      for (const ratio of [0, .5, 1]) {
        const y = bottom - ratio * (bottom - top)
        ctx.fillText(valueText(min + (max - min) * ratio, '', 2), 0, y + 4)
        ctx.fillStyle = '#c8d7d6'
        ctx.fillRect(left, y, right - left, 1)
        ctx.fillStyle = '#486269'
      }
      ctx.fillText(hours + 'h ago', left, height - 5)
      ctx.textAlign = 'right'
      ctx.fillText('Now', right, height - 5)
      ctx.save()
      ctx.beginPath()
      ctx.rect(left - 3, top - 3, right - left + 6, bottom - top + 6)
      ctx.clip()
      ctx.strokeStyle = ctx.fillStyle = '#176b68'
      ctx.lineWidth = 2
      let previous: { time: number; x: number; y: number } | undefined
      const maxGap = resolution === 'hour' ? 5400000 : 300000
      for (const [stamp, value] of points) {
        if (value == null) {
          previous = undefined
          continue
        }
        const time = Date.parse(stamp)
        const x = left + (time - start) / (end - start) * (right - left)
        const y = bottom - (chartValue(value, metric) - min) / (max - min) * (bottom - top)
        ctx.beginPath()
        if (previous && time - previous.time <= maxGap) {
          ctx.moveTo(previous.x, previous.y)
          ctx.lineTo(x, y)
          ctx.stroke()
        }
        ctx.beginPath()
        ctx.arc(x, y, 1.6, 0, 2 * Math.PI)
        ctx.fill()
        previous = { time, x, y }
      }
      ctx.restore()
    }
    draw()
    const observer = new ResizeObserver(draw)
    observer.observe(element)
    return () => observer.disconnect()
  }, [points, hours, metric, resolution])
  const latest = points.findLast(([, value]) => value != null)?.[1]
  const lastValue = metric.unit === ' MiB/s' ? rate(latest) : valueText(latest, metric.unit)
  return <canvas ref={canvas} role="img" aria-label={metric.label + ' history. Last recorded value ' + lastValue} />
}

export function HistoryChart({ history, hours, setHours }: {
  history: History | null; hours: number; setHours: (value: number) => void
}) {
  const [key, setKey] = useState(metrics[0].key)
  const metric = metrics.find(item => item.key === key)!
  const points = history?.series[key]
  return <section className="history" aria-labelledby="history-heading">
    <div className="section-heading">
      <div><h2 id="history-heading">Metric history</h2>
        <p>{history?.resolution === 'hour' ? 'Hourly averages' : 'Recorded samples'}</p></div>
      <div className="controls">
        <select aria-label="Metric" value={key} onChange={event => setKey(event.target.value)}>
          {metrics.map(item => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
        <select aria-label="History range" value={hours} onChange={event => setHours(Number(event.target.value))}>
          <option value={6}>Last 6 hours</option><option value={24}>Last 24 hours</option>
          <option value={168}>Last 7 days</option><option value={2160}>Last 90 days</option>
        </select>
      </div>
    </div>
    {history && points?.some(([, value]) => value != null)
      ? <Graph points={points} hours={hours} metric={metric} resolution={history.resolution} />
      : <p className="chart-empty">{history ? 'No readings for this metric in the selected range.' : 'Loading history…'}</p>}
  </section>
}
