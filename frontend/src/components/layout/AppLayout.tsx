import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Sidebar, navItems } from './Sidebar';
import { ConnectionIndicator } from '../common/ConnectionIndicator';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  // Close mobile menu on route change
  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-canvas flex-col lg:flex-row">
      {/* Desktop Sidebar (hidden on mobile/tablet < 1024px) */}
      <div className="hidden lg:flex shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Top Header (visible on < 1024px) */}
      <header className="lg:hidden h-14 bg-canvas border-b border-border px-4 flex items-center justify-between sticky top-0 z-40 select-none">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-input bg-charcoal text-white flex items-center justify-center font-bold text-xs shadow-sm">
            1M
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-[15px] leading-tight text-charcoal tracking-tight">
              OneMate
            </span>
            <span className="text-[10px] font-medium text-charcoal-caption leading-tight">
              Material Harmonization
            </span>
          </div>
        </div>

        {/* Right actions: Status + Menu toggle */}
        <div className="flex items-center gap-2">
          <div className="scale-90 origin-right">
            <ConnectionIndicator />
          </div>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            className="p-1.5 rounded-input border border-border text-charcoal hover:bg-surface-secondary transition-colors"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu Drawer Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-14 z-30 bg-black/40 animate-in fade-in duration-150">
          <nav className="bg-canvas border-b border-border p-4 shadow-lg flex flex-col gap-1 max-h-[calc(100vh-3.5rem)] overflow-y-auto">
            <div className="px-2 pb-1 text-[10px] font-semibold text-charcoal-caption uppercase tracking-wider">
              Operations Navigation
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-input text-body font-medium transition-colors ${
                      isActive
                        ? 'bg-surface text-charcoal font-semibold border border-border shadow-xs'
                        : 'text-charcoal-muted hover:bg-surface-secondary hover:text-charcoal'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      )}

      {/* Main Content Viewport */}
      <main className="flex-1 flex flex-col min-w-0 bg-canvas overflow-y-auto overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  );
};

