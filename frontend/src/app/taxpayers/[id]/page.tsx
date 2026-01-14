'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { taxpayersApi, derivedGroupsApi } from '@/lib/api';
import { formatCurrency, formatDate, formatPercentage } from '@/lib/utils';
import RiskBadge from '@/components/RiskBadge';

export default function TaxpayerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taxpayerId = parseInt(params.id as string);

  const { data: taxpayer, isLoading } = useQuery({
    queryKey: ['taxpayer', taxpayerId],
    queryFn: async () => {
      const response = await taxpayersApi.get(taxpayerId);
      return response.data;
    },
  });

  const { data: derivedGroups = [] } = useQuery({
    queryKey: ['derived-groups-taxpayer', taxpayerId],
    queryFn: async () => {
      const response = await derivedGroupsApi.forTaxpayer(taxpayerId);
      return response.data;
    },
    enabled: !!taxpayer,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!taxpayer) return <div>Wajib Pajak tidak ditemukan</div>;

  return (
    <div className="min-h-screen">
      <header className="bg-white/70 backdrop-blur border-b border-white/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button onClick={() => router.back()} className="btn-secondary mb-2">
            ← Kembali
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{taxpayer.name}</h1>
          <p className="text-sm text-gray-600">{taxpayer.npwp_masked}</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Profile Info */}
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Informasi Profil</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Jenis Entitas</p>
              <p className="font-medium">{taxpayer.entity_type || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className="font-medium">{taxpayer.status || '-'}</p>
            </div>
            <div className="col-span-2 md:col-span-1">
              <p className="text-sm text-gray-600">Grup</p>
              {taxpayer.group ? (
                <button
                  onClick={() => router.push(`/groups/${taxpayer.group.id}`)}
                  className="font-medium text-primary-600 hover:underline"
                >
                  {taxpayer.group.name}
                </button>
              ) : (
                <p className="font-medium">-</p>
              )}
            </div>
            {taxpayer.address && (
              <div className="col-span-2 md:col-span-3">
                <p className="text-sm text-gray-600">Alamat</p>
                <p className="text-sm">{taxpayer.address}</p>
              </div>
            )}
          </div>

          {/* Beneficial Owners */}
          {taxpayer.beneficial_owners && taxpayer.beneficial_owners.length > 0 && (
            <div className="mt-6">
              <p className="text-sm text-gray-600 mb-2">Beneficial Owners</p>
              <div className="space-y-2">
                {taxpayer.beneficial_owners.map((bo: any) => (
                  <div key={bo.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <button
                      onClick={() => router.push(`/beneficial-owners/${bo.id}`)}
                      className="font-medium text-primary-600 hover:underline"
                    >
                      {bo.name}
                    </button>
                    {bo.ownership_pct && (
                      <span className="text-sm text-gray-600">{bo.ownership_pct}%</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Financial Data */}
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Data Keuangan Tahunan</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tahun</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Omset</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Kompensasi Rugi</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status SPT</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {taxpayer.yearly_financials?.map((fin: any) => (
                  <tr key={fin.tax_year}>
                    <td className="px-4 py-3 whitespace-nowrap font-medium">{fin.tax_year}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{formatCurrency(fin.turnover)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{formatCurrency(fin.loss_compensation)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{fin.spt_status || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Ratios */}
        <div className="card">
          <h3 className="font-semibold text-lg mb-4">Rasio Keuangan</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tahun</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">NPM</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ETR</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">CTTOR</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {[2022, 2023, 2024, 2025].map(year => {
                  const ratios = taxpayer.yearly_ratios?.filter((r: any) => r.tax_year === year) || [];
                  const npm = ratios.find((r: any) => r.ratio_code === 'NPM');
                  const etr = ratios.find((r: any) => r.ratio_code === 'ETR');
                  const cttor = ratios.find((r: any) => r.ratio_code === 'CTTOR');

                  return (
                    <tr key={year}>
                      <td className="px-4 py-3 whitespace-nowrap font-medium">{year}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatPercentage(npm?.ratio_value)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatPercentage(etr?.ratio_value)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{cttor?.ratio_value?.toFixed(2) || '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Treatment History */}
        {taxpayer.treatment_histories && taxpayer.treatment_histories.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-lg mb-4">Riwayat Tindakan</h3>
            <div className="space-y-3">
              {taxpayer.treatment_histories.map((treatment: any) => (
                <div key={treatment.id} className="border-l-4 border-primary-500 pl-4 py-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{treatment.treatment_type}</p>
                      <p className="text-sm text-gray-600">{formatDate(treatment.treatment_date)}</p>
                      {treatment.notes && <p className="text-sm mt-1">{treatment.notes}</p>}
                    </div>
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded">{treatment.outcome}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Risks */}
        {taxpayer.risks && taxpayer.risks.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-lg mb-4">Penilaian Risiko</h3>
            <div className="space-y-3">
              {taxpayer.risks.map((risk: any) => (
                <div key={risk.id} className="p-3 bg-gray-50 rounded">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{risk.risk_source}</span>
                    {risk.risk_level && <RiskBadge level={risk.risk_level} />}
                  </div>
                  {risk.risk_score && (
                    <p className="text-sm text-gray-600">Skor: {risk.risk_score}</p>
                  )}
                  {risk.notes && (
                    <p className="text-sm text-gray-600 mt-1">{risk.notes}</p>
                  )}
                  {risk.tax_year && (
                    <p className="text-xs text-gray-500 mt-1">Tahun: {risk.tax_year}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Derived Group Candidates */}
        {derivedGroups && derivedGroups.length > 0 && (
          <div className="card bg-blue-50 border-blue-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-lg">Grup Derivasi (Kandidat)</h3>
              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {derivedGroups.length} grup
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-4">
              Grup yang diturunkan dari analisis hubungan istimewa berdasarkan rule set aktif.
            </p>
            <div className="space-y-3">
              {derivedGroups.map((dg: any) => (
                <div
                  key={dg.derived_group_id}
                  onClick={() => router.push(`/derived-groups/${dg.derived_group_id}`)}
                  className="p-4 bg-white border border-blue-200 rounded hover:shadow-md cursor-pointer transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{dg.group_key}</p>
                      <p className="text-sm text-gray-600 mt-1">{dg.rule_set_name}</p>
                      <p className="text-xs text-gray-500 mt-2">{dg.reason_snippet}</p>
                    </div>
                    <div className="text-right ml-4">
                      <p className="text-sm font-medium text-blue-700">
                        Skor: {dg.strength_score || 'N/A'}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {dg.member_count} anggota
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
