import { NextResponse } from 'next/server';
import { getAllJobIds } from '@/lib/db';

// Static demo: tailored .docx files live on the local machine, not on the
// deployed site, so downloads are unavailable here. Prerender false for all.
export const dynamic = 'force-static';

export function generateStaticParams() {
  return getAllJobIds().map((id) => ({ id: String(id) }));
}

export async function GET() {
  return NextResponse.json({ exists: false, filename: '' });
}
