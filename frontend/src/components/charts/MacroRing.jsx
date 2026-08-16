import {
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  PolarAngleAxis,
} from 'recharts'
import { macroPercent } from '../../utils/macros'

export default function MacroRing({ consumed, target, label, color = '#c4b5fd' }) {
  const percent = macroPercent(consumed, target)
  const chartData = [{ name: label, value: percent, fill: color }]

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-40 w-40 sm:h-44 sm:w-44">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="72%"
            outerRadius="100%"
            data={chartData}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar
              background={{ fill: 'rgba(255,255,255,0.18)' }}
              dataKey="value"
              cornerRadius={12}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-white sm:text-3xl">{Math.round(consumed)}</span>
          <span className="text-xs text-white/70">/ {target} kcal</span>
          <span className="mt-1 text-xs font-medium text-white/80">{percent}%</span>
        </div>
      </div>
      <p className="mt-2 text-sm font-semibold text-white">{label}</p>
    </div>
  )
}
