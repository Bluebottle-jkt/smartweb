'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { derivedGroupsApi } from '@/lib/api';

export default function DerivedGroupDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = parseInt(params.id as string);

  const { data: group, isLoading } = useQuery({
    queryKey: ['derived-group', groupId],
    queryFn: async () => {
      const response = await derivedGroupsApi.get(groupId);
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!group) return <div>Grup derivasi tidak ditemukan</div>;

  return (
    <div className="min-h-screen">
      <header className="bg-white/70 backdrop-blur border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button onClick={() => router.back()} className="btn-secondary mb-2">
            ← Kembali
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{group.group_key}</h1>
              <p className="text-sm text-gray-600 mt-1">{group.rule_set_name}</p>
            </div>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
              Grup Derivasi
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Metadata Card */}
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Informasi Derivasi</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Generated At</p>
              <p className="font-medium">{new Date(group.generated_at).toLocaleString('id-ID')}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">As of Date</p>
              <p className="font-medium">{group.as_of_date || 'Current'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Jumlah Anggota</p>
              <p className="font-medium">{group.members?.length || 0}</p>
            </div>
            {group.summary && (
              <>
                <div>
                  <p className="text-sm text-gray-600">Root Taxpayer ID</p>
                  <p className="font-medium">{group.summary.root_taxpayer_id}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-sm text-gray-600">Rule Set</p>
                  <p className="font-medium">{group.summary.generated_with_rule}</p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Members Table */}
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">
            Daftar Anggota ({group.members?.length || 0})
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Nama
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    NPWP
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Strength Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Koneksi
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Jalur
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {group.members?.map((member: any) => (
                  <tr
                    key={member.taxpayer_id}
                    onClick={() => router.push(`/taxpayers/${member.taxpayer_id}`)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <p className="font-medium text-gray-900">{member.name}</p>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {member.npwp_masked}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                        {member.strength_score || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {member.evidence_summary?.total_connections || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {member.evidence_summary?.path_count || 0} jalur
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Evidence Note */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">Catatan Evidence</h4>
          <p className="text-sm text-blue-800">
            Grup ini diturunkan menggunakan analisis graph dari hubungan istimewa.
            Strength score menunjukkan kekuatan koneksi masing-masing anggota dalam grup.
            Untuk detail jalur hubungan, klik pada nama wajib pajak untuk melihat evidence lengkap.
          </p>
        </div>
      </main>
    </div>
  );
}
