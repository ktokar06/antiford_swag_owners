import React from 'react';
import { NavLink, Outlet, Link } from 'react-router-dom';
import { LayoutDashboard, Phone, Hash, Network, Ban, SlidersHorizontal, LogOut, User, Shield, FileText } from 'lucide-react';
import { useAuth } from '@/libs/AuthContext';
import { cn } from '@/libs/utils';

const NAV = [
  { to: '/', label: 'Обзор', icon: LayoutDashboard, end: true },
  { to: '/calls', label: 'Вызовы', icon: Phone },
  { to: '/numbers', label: 'Номера', icon: Hash },
  { to: '/graph', label: 'Граф', icon: Network },
  { to: '/blocks', label: 'Блокировки', icon: Ban },
  { to: '/cdr', label: 'Записи CDR', icon: FileText },
  { to: '/rules', label: 'Модель и политика', icon: SlidersHorizontal },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const roleLabel = 'Оператор';

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-card lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:left-0 lg:h-screen lg:overflow-y-auto">
        <div className="px-5 py-6">
          <Link to="/" className="font-display text-lg font-semibold tracking-tight">
            Антифрод
          </Link>
          <p className="mt-1 text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
            SWAG OWNERS
          </p>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-4">
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              )
            }
          >
            {user?.avatar_url ? <img src={user.avatar_url} alt="" className="h-7 w-7 rounded-full object-cover" /> : <User className="h-4 w-4" />}
            Профиль
          </NavLink>

          <div className="mt-4 px-3">
            <p className="truncate text-xs font-medium text-foreground">{user?.email}</p>
            <p className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              <Shield className="h-3 w-3" />
              {roleLabel}
            </p>
          </div>

          <button
            onClick={() => logout()}
            className="mt-3 inline-flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-muted-foreground hover:bg-accent/50 hover:text-foreground"
          >
            <LogOut className="h-3.5 w-3.5" />
            Выйти
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0 lg:pl-60">
        <nav aria-label="Навигация" className="flex flex-wrap gap-3 border-b border-border p-4 lg:hidden">
          {NAV.map(({to, label}) => <NavLink key={to} to={to} className="text-sm underline-offset-4 hover:underline">{label}</NavLink>)}
          <NavLink to="/profile" className="text-sm">Профиль</NavLink>
          <button onClick={() => logout()} className="text-sm">Выйти</button>
        </nav>
        <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
