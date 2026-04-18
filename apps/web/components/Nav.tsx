import Link from 'next/link';

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/chat', label: 'Chat' },
  { href: '/compare', label: 'Compare' },
];

export function Nav() {
  return (
    <header className="topbar">
      <div className="brand-wrap">
        <span className="brand-chip">Project 7</span>
        <h1>ESG Intelligence Platform</h1>
      </div>
      <nav>
        {links.map((link) => (
          <Link key={link.href} href={link.href} className="nav-link">
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
