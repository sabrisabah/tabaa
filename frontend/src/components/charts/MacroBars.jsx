import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { macroPercent } from '../../utils/macros'

const MACRO_META = [
  { key: 'protein', label: 'Protein', color: '#c4b5fd' },
  { key: 'carbs', label: 'Carbs', color: '#fbbf24' },
  { key: 'fats', label: 'Fats', color: '#67e8f9' },
]

function MacroTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-xl border border-white/30 bg-violet-950/90 px-3 py-2 text-sm text-white shadow-lg backdrop-blur-md">
      <p className="font-medium">{item.label}</p>
      <p className="text-white/75">
        {Math.round(item.consumed)}g / {item.target}g ({item.percent}%)
      </p>
    </div>
  )
}

export default function MacroBars({ consumed, targets }) {
  const data = MACRO_META.map(({ key, label, color }) => {
    const value = consumed?.[key] ?? 0
    const target = targets?.[key] ?? 0
    return {
      key,
      label,
      color,
      consumed: value,
      target,
      percent: macroPercent(value, target),
      barValue: macroPercent(value, target),
    }
  })

  return (
    <div className="rounded-2xl border border-white/25 bg-white/10 p-4 backdrop-blur-sm">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-white/80">
        Macronutrients
      </h3>
      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category"
              dataKey="label"
              width={64}
              tick={{ fill: 'rgba(255,255,255,0.85)', fontSize: 13 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<MacroTooltip />} cursor={{ fill: 'transparent' }} />
            <Bar dataKey="barValue" radius={[0, 8, 8, 0]} barSize={18} background={{ fill: 'rgba(255,255,255,0.12)' }}>
              {data.map((entry) => (
                <Cell key={entry.key} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs text-white/75">
        {data.map((item) => (
          <div key={item.key}>
            <span className="font-semibold text-white">{Math.round(item.consumed)}g</span>
            <span className="text-white/50"> / {item.target}g</span>
          </div>
        ))}
      </div>
    </div>
  )
}
