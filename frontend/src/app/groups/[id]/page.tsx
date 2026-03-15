'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { groupsApi, exportsApi } from '@/lib/api';
import { formatCurrency, downloadCSV } from '@/lib/utils';
import RiskBadge from '@/components/RiskBadge';
import MainLayout from '@/components/MainLayout';

export default function GroupDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = parseInt(params.id as string);
  const [selectedMember, setSelectedMember] = useState<any | null>(null);

  const { data: group, isLoading } = useQuery({
    queryKey: ['group', groupId],
    queryFn: async () => {
      const response = await groupsApi.get(groupId);
      return response.data;
    },
  });

  const handleExport = async () => {
    try {
      const response = await exportsApi.groupMembers(groupId);
      downloadCSV(response.data, `grup_${groupId}_anggota.csv`);
    } catch (error) {
      alert('Gagal mengekspor data');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!group) return <div>Grup tidak ditemukan</div>;

  return (
    <MainLayout title={group.name}>
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <button onClick={() => router.back()} className="btn-secondary">
            ← Kembali
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{group.name}</h1>
            <p className="text-sm text-gray-600">{group.sector || 'Tidak ada sektor'}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Info Card */}
          <div className="card">
            <h3 className="font-semibold text-lg mb-4">Informasi Grup</h3>
            <div className="space-y-2">
              <div>
                <span className="text-sm text-gray-600">Jumlah Anggota:</span>
                <p className="font-medium">{group.member_count}</p>
              </div>
              {group.notes && (
                <div>
                  <span className="text-sm text-gray-600">Catatan:</span>
                  <p className="text-sm">{group.notes}</p>
                </div>
              )}
            </div>
            <button onClick={handleExport} className="btn-primary w-full mt-4">
              Ekspor ke CSV
            </button>
          </div>

          {/* Risk Summary */}
          <div className="card lg:col-span-2">
            <h3 className="font-semibold text-lg mb-4">Ringkasan Risiko</h3>
            {group.aggregates?.risk_summary && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600 mb-2">Distribusi Risiko CRM:</p>
                  <div className="space-y-1">
                    {Object.entries(group.aggregates.risk_summary.crm_risk_distribution).map(([level, count]: [string, any]) => (
                      <div key={level} className="flex items-center justify-between">
                        <RiskBadge level={level} />
                        <span className="text-sm font-medium">{count} WP</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-2">Skor Group Engine:</p>
                  <p className="text-2xl font-bold">
                    {group.aggregates.risk_summary.avg_group_engine_score?.toFixed(1) || 'N/A'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Members List */}
        <div className="card mt-6">
          <h3 className="font-semibold text-lg mb-4">Daftar Anggota ({group.member_count})</h3>
          <p className="text-xs text-gray-500 mb-3">Klik anggota untuk melihat agregat tahunan</p>
          <div className="space-y-2">
            {group.members?.map((member: any) => (
              <div
                key={member.id}
                onClick={() => setSelectedMember(selectedMember?.id === member.id ? null : member)}
                className={`p-4 border rounded cursor-pointer transition-colors ${
                  selectedMember?.id === member.id
                    ? 'border-indigo-400 bg-indigo-50'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{member.name}</p>
                    <p className="text-sm text-gray-600">{member.npwp_masked}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">{member.role}</p>
                    <p className="text-xs text-gray-500">{member.status}</p>
                    <button
                      onClick={(e) => { e.stopPropagation(); router.push(`/taxpayers/${member.id}`); }}
                      className="text-xs text-indigo-600 hover:underline mt-1"
                    >
                      Detail →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Agregat Tahunan — only shown when a member is selected */}
        {selectedMember && (
          <div className="card mt-6">
            <h3 className="font-semibold text-lg mb-1">Agregat Tahunan — {selectedMember.name}</h3>
            <p className="text-xs text-gray-500 mb-4">Data per tahun untuk anggota ini</p>
            {selectedMember.yearly_aggregates?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tahun</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total Omset</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Afiliasi Domestik</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Afiliasi LN</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {selectedMember.yearly_aggregates.map((yr: any) => (
                      <tr key={yr.year}>
                        <td className="px-6 py-4 whitespace-nowrap font-medium">{yr.year}</td>
                        <td className="px-6 py-4 whitespace-nowrap">{formatCurrency(yr.total_turnover)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">{formatCurrency(yr.affiliate_domestic)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">{formatCurrency(yr.affiliate_foreign)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-500 py-4">Tidak ada data agregat tahunan tersedia. Lihat detail lengkap di halaman WP.</p>
            )}
            <div className="mt-4">
              <button
                onClick={() => router.push(`/taxpayers/${selectedMember.id}`)}
                className="btn-primary text-sm"
              >
                Buka Detail WP →
              </button>
            </div>
          </div>
        )}
        </div>
    </MainLayout>
  );
}
