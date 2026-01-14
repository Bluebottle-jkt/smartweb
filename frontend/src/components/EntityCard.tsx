'use client';

interface EntityCardProps {
  title: string;
  subtitle?: string;
  type: 'group' | 'taxpayer' | 'beneficial-owner';
  onClick?: () => void;
  children?: React.ReactNode;
}

export default function EntityCard({ title, subtitle, type, onClick, children }: EntityCardProps) {
  const typeColors = {
    'group': 'bg-blue-100 text-blue-800',
    'taxpayer': 'bg-green-100 text-green-800',
    'beneficial-owner': 'bg-purple-100 text-purple-800',
  };

  const typeLabels = {
    'group': 'Grup',
    'taxpayer': 'Wajib Pajak',
    'beneficial-owner': 'Beneficial Owner',
  };

  return (
    <div
      className={`card ${onClick ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
        </div>
        <span className={`px-3 py-1 text-xs font-medium rounded-full ${typeColors[type]}`}>
          {typeLabels[type]}
        </span>
      </div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
