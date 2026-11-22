import type { Collector, Snapshot } from './api'
import { capacity, duration, rate, valueText } from './format'

const summary = [
  ['CPU', 'cpu_percent', '%'],
  ['RAM', 'ram_percent', '%'],
  ['Swap', 'swap_percent', '%'],
  ['Disk peak', 'disk_percent', '%'],
  ['Temperature peak', 'temperature_celsius', ' °C'],
  ['Download', 'download_bytes_per_second', ' MiB/s'],
  ['Upload', 'upload_bytes_per_second', ' MiB/s'],
]

const collectorNames: Record<Collector, string> = {
  cpu: 'CPU', memory: 'Memory', disk: 'Disk', network: 'Network',
  temperature: 'Temperature', system: 'System',
}

function Freshness({ snapshot, collector }: { snapshot: Snapshot; collector: Collector }) {
  const { status, age_seconds } = snapshot.freshness[collector]
  return <span className={'sample ' + status}>
    {status === 'unavailable' ? 'Unavailable' : `${status === 'stale' ? 'Stale · ' : ''}${duration(age_seconds)} ago`}
  </span>
}

function Detail({ rows }: { rows: [string, string][] }) {
  return <div className="reading-detail">
    {rows.length ? <dl>{rows.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
      : <p>Unavailable</p>}
  </div>
}

export function Readings({ snapshot }: { snapshot: Snapshot }) {
  const data = snapshot.collectors
  const system = data?.system
  const details: Record<Collector, [string, string][]> = {
    cpu: [
      ['Logical cores', valueText(data?.cpu?.logical_cores, '', 0)],
      ['Load average (1m)', valueText(data?.cpu?.load_average?.['1m'], '', 2)],
    ],
    memory: [
      ['RAM used', capacity(data?.memory?.ram?.used_bytes)],
      ['RAM total', capacity(data?.memory?.ram?.total_bytes)],
      ['Swap used', capacity(data?.memory?.swap?.used_bytes)],
      ['Swap total', capacity(data?.memory?.swap?.total_bytes)],
    ],
    disk: (data?.disk?.filesystems ?? []).map(fs => [
      fs.mountpoint, `${valueText(fs.usage_percent, '%')} · ${capacity(fs.used_bytes)} used`,
    ]),
    network: Object.entries(data?.network?.interfaces ?? {}).filter(([, info]) => info.type !== 'loopback')
      .map(([name, info]) => [name, `${rate(info.download_bytes_per_second)} down · ${rate(info.upload_bytes_per_second)} up`]),
    temperature: Object.entries(data?.temperature ?? {}).flatMap(([name, sensors]) => sensors.map(
      (sensor, index): [string, string] => [
        name + ' / ' + (sensor.label || (index + 1)), valueText(sensor.current_celsius, ' °C'),
      ],
    )),
    system: [
      ['OS', system?.distribution ?? system?.os ?? 'Unavailable'],
      ['Kernel', system?.kernel ?? 'Unavailable'],
      ['Architecture', system?.architecture ?? 'Unavailable'],
      ['Uptime', duration(system?.uptime_seconds)],
      ['Power profile', system?.power_profile?.name ?? 'Unavailable'],
    ],
  }
  const collectors = Object.keys(collectorNames) as Collector[]
  return <>
    <section aria-labelledby="readings-heading">
      <h2 id="readings-heading">Current readings</h2>
      <dl className="readings">
        {summary.map(([label, key, unit]) => <div key={key}>
          <dt>{label}</dt>
          <dd className={snapshot.summary[key] == null ? 'unavailable-value' : undefined}>
            {unit === ' MiB/s' ? rate(snapshot.summary[key]) : valueText(snapshot.summary[key], unit)}
          </dd>
        </div>)}
      </dl>
    </section>
    <section aria-labelledby="collectors-heading">
      <h2 id="collectors-heading">Collectors</h2>
      <div className="collector-list">
        {collectors.filter(collector => data || collector !== 'system').map(collector => <div key={collector}>
          <h3>{collectorNames[collector]}</h3>
          <Freshness snapshot={snapshot} collector={collector} />
          {data && <Detail rows={details[collector]} />}
        </div>)}
      </div>
    </section>
  </>
}
