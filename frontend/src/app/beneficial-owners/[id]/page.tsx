'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { beneficialOwnersApi, derivedGroupsApi } from '@/lib/api';

export default function BeneficialOwnerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const boId = parseInt(params.id as string);

  const { data: bo, isLoading } = useQuery({
    queryKey: ['beneficial-owner', boId],
    queryFn: async () => {
      const response = await beneficialOwnersApi.get(boId);
      return response.data;
    },
  });

  const { data: derivedGroups = [] } = useQuery({
    queryKey: ['derived-groups-bo', boId],
    queryFn: async () => {
      const response = await derivedGroupsApi.forBeneficialOwner(boId);
      return response.data;
    },
    enabled: !!bo,
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (!bo) return <div>Beneficial Owner tidak ditemukan</div>;

  return (
    <div className="min-h-screen">
      <header className="bg-white/70 backdrop-blur border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button onClick={() => router.back()} className="btn-secondary mb-2">← Kembali</button>
          <h1 className="text-2xl font-bold text-gray-900">{bo.name}</h1>
          <p className="text-sm text-gray-600">{bo.nationality}</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Wajib Pajak Terkait ({bo.taxpayers?.length || 0})</h3>
          <div className="space-y-2">
            {bo.taxpayers?.map((tp: any) => (
              <div key={tp.id} onClick={() => router.push(`/taxpayers/${tp.id}`)} className="p-3 border rounded hover:bg-gray-50 cursor-pointer">
                <div className="flex justify-between">
                  <div>
                    <p className="font-medium">{tp.name}</p>
                    <p className="text-sm text-gray-600">{tp.npwp_masked}</p>
                  </div>
                  {tp.ownership_pct && <span className="text-sm">{tp.ownership_pct}%</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Grup Terkait ({bo.groups?.length || 0})</h3>
          <div className="space-y-2">
            {bo.groups?.map((group: any) => (
              <div key={group.id} onClick={() => router.push(`/groups/${group.id}`)} className="p-3 border rounded hover:bg-gray-50 cursor-pointer">
                <p className="font-medium">{group.name}</p>
                <p className="text-sm text-gray-600">{group.sector}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Derived Groups (Indikasi) */}
        {derivedGroups && derivedGroups.length > 0 && (
          <div className="card bg-purple-50 border-purple-200">
            <h3 className="font-semibold text-lg mb-4">Grup Derivasi (Indikasi)</h3>
            <p className="text-sm text-gray-700 mb-4">
              Grup derivasi yang terkait dengan wajib pajak yang dimiliki beneficial owner ini.
            </p>
            <div className="space-y-2">
              {derivedGroups.map((dg: any) => (
                <div
                  key={dg.derived_group_id}
                  onClick={() => router.push(`/derived-groups/${dg.derived_group_id}`)}
                  className="p-3 bg-white border border-purple-200 rounded hover:shadow-md cursor-pointer transition-shadow"
                >
                  <p className="font-medium">{dg.group_key}</p>
                  <p className="text-sm text-gray-600">{dg.rule_set_name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Terkait via: {dg.related_via_taxpayer} • {dg.member_count} anggota
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
