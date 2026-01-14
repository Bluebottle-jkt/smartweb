interface RiskBadgeProps {
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY_HIGH' | string;
}

export default function RiskBadge({ level }: RiskBadgeProps) {
  const config: Record<string, { label: string; className: string }> = {
    LOW: { label: 'Rendah', className: 'bg-green-100 text-green-800' },
    MEDIUM: { label: 'Sedang', className: 'bg-yellow-100 text-yellow-800' },
    HIGH: { label: 'Tinggi', className: 'bg-orange-100 text-orange-800' },
    VERY_HIGH: { label: 'Sangat Tinggi', className: 'bg-red-100 text-red-800' },
  };

  const { label, className } = config[level] || { label: level, className: 'bg-gray-100 text-gray-800' };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${className}`}>
      {label}
    </span>
  );
}
