import { NextResponse } from 'next/server';
import { getAllJobIds } from '@/lib/db';

// Static demo: tailored .docx files are generated on the local machine and are
// not part of the deployed site, so downloads are unavailable here.
export const dynamic = 'force-static';

export function generateStaticParams() {
  return getAllJobIds().map((id) => ({ id: String(id) }));
}

export async function GET() {
  return NextResponse.json(
    { error: 'Demo 模式不提供简历下载（定制简历在本地生成）' },
    { status: 404 },
  );
}
