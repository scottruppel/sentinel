import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '◈' },
  { to: '/boms', label: 'BOM Manager', icon: '☰' },
  { to: '/risk', label: 'Risk Analysis', icon: '⚠' },
  { to: '/exposure', label: 'Cross-exposure', icon: '⎘' },
  { to: '/whatif', label: 'What-If', icon: '⇄' },
];

export default function Sidebar() {
  return (
    <aside className="w-56 bg-sentinel-900 text-white flex flex-col min-h-screen">
      <div className="p-4 border-b border-sentinel-700">
        <h1 className="text-xl font-bold tracking-wide">SENTINEL</h1>
        <p className="text-xs text-sentinel-200 mt-1">DMSMS Intelligence</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                isActive
                  ? 'bg-sentinel-700 text-white'
                  : 'text-sentinel-200 hover:bg-sentinel-700/50'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
