import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  CheckSquare,
  ShieldCheck,
  History,
} from 'lucide-react';
import { ConnectionIndicator } from '../common/ConnectionIndicator';

export interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

export const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'CPSEs', path: '/cpses', icon: Building2 },
  { name: 'Review Queue', path: '/review', icon: CheckSquare },
  { name: 'National Materials', path: '/national-materials', icon: ShieldCheck },
  { name: 'Audit Trail', path: '/audit', icon: History },
];



export const Sidebar: React.FC = () => {
  return (
    <aside className="w-60 bg-canvas border-r border-border flex flex-col h-screen select-none shrink-0 sticky top-0">
      {/* Brand Header */}
      <div className="h-14 px-4 flex items-center gap-2.5 border-b border-border/80">
        <div className="w-7 h-7 rounded-input bg-charcoal text-white flex items-center justify-center font-bold text-xs shadow-sm">
          1M
        </div>
        <div className="flex flex-col">
          <span className="font-semibold text-[15px] leading-tight text-charcoal tracking-tight">
            OneMate
          </span>
          <span className="text-[11px] font-medium text-charcoal-caption leading-tight">
            Material Harmonization
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-2 pb-2 text-[10px] font-semibold text-charcoal-caption uppercase tracking-wider">
          Operations
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-2 rounded-input text-body font-medium transition-colors ${
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

      {/* Footer / Status */}
      <div className="p-3 border-t border-border/80 bg-canvas">
        <ConnectionIndicator />
      </div>
    </aside>
  );
};
