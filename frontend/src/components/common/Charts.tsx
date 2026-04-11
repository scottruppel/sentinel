import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const RISK_COLORS = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

interface RiskRadarProps {
  lifecycle: number;
  supply: number;
  geographic: number;
  supplier: number;
  regulatory: number;
  size?: number;
}

export function RiskRadar({ lifecycle, supply, geographic, supplier, regulatory, size = 250 }: RiskRadarProps) {
  const data = [
    { dimension: 'Lifecycle', score: lifecycle },
    { dimension: 'Supply', score: supply },
    { dimension: 'Geographic', score: geographic },
    { dimension: 'Supplier', score: supplier },
    { dimension: 'Regulatory', score: regulatory },
  ];

  return (
    <ResponsiveContainer width="100%" height={size}>
      <RadarChart data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="dimension" className="text-xs" />
        <PolarRadiusAxis domain={[0, 100]} tick={false} />
        <Radar dataKey="score" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.3} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

interface RiskDistributionProps {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export function RiskDistribution({ critical, high, medium, low }: RiskDistributionProps) {
  const data = [
    { name: 'Critical', count: critical, color: RISK_COLORS.critical },
    { name: 'High', count: high, color: RISK_COLORS.high },
    { name: 'Medium', count: medium, color: RISK_COLORS.medium },
    { name: 'Low', count: low, color: RISK_COLORS.low },
  ];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count">
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RiskPie({ critical, high, medium, low }: RiskDistributionProps) {
  const data = [
    { name: 'Critical', value: critical, color: RISK_COLORS.critical },
    { name: 'High', value: high, color: RISK_COLORS.high },
    { name: 'Medium', value: medium, color: RISK_COLORS.medium },
    { name: 'Low', value: low, color: RISK_COLORS.low },
  ].filter((d) => d.value > 0);

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}
