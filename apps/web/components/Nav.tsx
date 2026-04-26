'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/', label: 'Home' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/predictions', label: 'Predictions' },
  { href: '/chat', label: 'Chat' },
  { href: '/compare', label: 'Compare' },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="topbar">
      <Link href="/" className="brand-wrap">
        <span className="brand-chip">Project 7</span>
        <div>
          <h1>HKEX ESG Intelligence</h1>
          <p className="brand-subtitle">Chat, compare, and audit company disclosures without hunting for raw IDs.</p>
        </div>
      </Link>
      <nav className="topnav">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`nav-link${pathname === link.href ? ' active' : ''}`}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
