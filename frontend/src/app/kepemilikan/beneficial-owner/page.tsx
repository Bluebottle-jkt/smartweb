'use client';
import ComingSoonPage from '@/components/ComingSoonPage';

export default function BeneficialOwnerPage() {
  return (
    <ComingSoonPage
      title="Beneficial Owner"
      description="Daftar beneficial owner dan hubungan kepemilikan"
      icon={<svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}
    />
  );
}