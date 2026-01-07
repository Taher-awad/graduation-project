import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  Box, 
  LogOut, 
  LayoutDashboard, 
  Users, 
  Settings 
} from 'lucide-react';
import clsx from 'clsx';

const SidebarItem = ({ icon: Icon, label, path, active }: any) => (
  <Link
    to={path}
    className={clsx(
      "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
      active 
        ? "bg-indigo-600 text-white" 
        : "text-slate-400 hover:bg-slate-800 hover:text-white"
    )}
  >
    <Icon size={20} />
    <span className="font-medium">{label}</span>
  </Link>
);

export const DashboardLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
            <Box size={20} className="text-white" />
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Cortex AI
          </h1>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-2">
          <SidebarItem 
            icon={LayoutDashboard} 
            label="Assets" 
            path="/" 
            active={location.pathname === '/' || location.pathname.startsWith('/assets')} 
          />
          <SidebarItem 
            icon={Users} 
            label="Rooms" 
            path="/rooms" 
            active={location.pathname.startsWith('/rooms')} 
          />
          <SidebarItem 
            icon={Settings} 
            label="Settings" 
            path="/settings" 
            active={location.pathname === '/settings'} 
          />
        </nav>

        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-4 px-2">
            <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-sm font-bold">
              {user?.username.substring(0, 2).toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-medium truncate">{user?.username}</p>
              <p className="text-xs text-slate-500 truncate">{user?.role}</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <header className="h-16 border-b border-slate-800 flex items-center px-8 justify-between">
            <h2 className="text-lg font-semibold text-slate-200">
                {location.pathname === '/' ? 'Asset Library' : 
                 location.pathname.startsWith('/rooms') ? 'Virtual Rooms' : 
                 'Dashboard'}
            </h2>
        </header>
        <div className="p-8">
            <Outlet />
        </div>
      </main>
    </div>
  );
};
