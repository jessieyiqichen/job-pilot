import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'JobPilot · 求职仪表盘',
  description: 'JobPilot — 智能求职数据看板',
};

function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center px-6">
        <Link
          href="/"
          className="text-lg font-bold tracking-tight text-gray-900 transition-colors hover:text-blue-600"
        >
          JobPilot
        </Link>
        <div className="ml-auto flex gap-6">
          <Link
            href="/"
            className="text-[14px] text-gray-500 transition-colors hover:text-gray-900"
          >
            岗位看板
          </Link>
          <Link
            href="/pipeline"
            className="text-[14px] text-gray-500 transition-colors hover:text-gray-900"
          >
            求职漏斗
          </Link>
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.loli.net" />
        <link rel="preconnect" href="https://gstatic.loli.net" crossOrigin="anonymous" />
        <link
          href="https://fonts.loli.net/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex min-h-full flex-col">
        <NavBar />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
