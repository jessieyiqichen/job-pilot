import { NextResponse } from 'next/server';
import { getJobById } from '@/lib/db';
import fs from 'fs';
import path from 'path';

const TAILORED_DIR = path.join(process.cwd(), '..', 'data', 'tailored');

function buildFilename(company: string, title: string): string {
  const safeCompany = company.replace(/\//g, '_').slice(0, 20);
  const safeTitle = title.replace(/\//g, '_').slice(0, 30);
  return `${safeCompany}_${safeTitle}.docx`;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const jobId = parseInt(id, 10);
    if (isNaN(jobId)) {
      return NextResponse.json({ error: 'Invalid job ID' }, { status: 400 });
    }

    const job = getJobById(jobId);
    if (!job) {
      return NextResponse.json({ error: 'Job not found' }, { status: 404 });
    }

    const filename = buildFilename(job.company, job.title);
    const filePath = path.join(TAILORED_DIR, filename);

    if (!fs.existsSync(filePath)) {
      return NextResponse.json(
        { error: 'Tailored resume not found', filename },
        { status: 404 },
      );
    }

    const fileBuffer = fs.readFileSync(filePath);

    return new Response(fileBuffer, {
      headers: {
        'Content-Type':
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
