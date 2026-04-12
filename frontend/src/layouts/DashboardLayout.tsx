import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { 
  Box, 
  LogOut, 
  LayoutDashboard, 
  Users, 
  Settings, 
  Sun, 
  Moon,
  ChevronRight
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const SidebarItem = ({ icon: Icon, label, path, active }: { icon: LucideIcon; label: string; path: string; active?: boolean }) => (
  <Link
    to={path}
    className={clsx(
      "group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
      active 
        ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/30" 
        : "text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/50 dark:hover:text-slate-200"
    )}
  >
    <Icon size={20} className={clsx(active ? "text-white" : "group-hover:text-indigo-500 transition-colors")} />
    <span className="font-medium flex-1">{label}</span>
    {active && <ChevronRight size={16} className="opacity-50" />}
  </Link>
);

export const DashboardLayout = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-300">
      {/* Sidebar */}
      <aside className="w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col shadow-xl z-10 transition-colors duration-300">
        <div className="p-8 flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Box size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                Cortex AI
            </h1>
            <p className="text-xs text-slate-400 font-medium tracking-wider">WORKSPACE</p>
          </div>
        </div>

        <nav className="flex-1 px-6 space-y-2.5">
          <p className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 mt-2">Menu</p>
          <SidebarItem 
            icon={LayoutDashboard} 
            label="Assets Library" 
            path="/" 
            active={location.pathname === '/' || location.pathname.startsWith('/assets')} 
          />
          <SidebarItem 
            icon={Users} 
            label="Virtual Rooms" 
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

        {/* User & Theme Section */}
        <div className="p-6 border-t border-slate-200 dark:border-slate-800 space-y-4">
            
            {/* Theme Toggle */}
            <div className="flex items-center justify-between px-4 py-2 bg-slate-100 dark:bg-slate-800/50 rounded-lg">
                <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Appearance</span>
                <button 
                    onClick={toggleTheme}
                    className="p-1.5 rounded-full hover:bg-white dark:hover:bg-slate-700 transition-colors text-slate-500 dark:text-slate-400"
                >
                    {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                </button>
            </div>

            <div className="flex items-center gap-3 px-2 py-2">
                <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-sm font-bold text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/30">
                {user?.username.substring(0, 2).toUpperCase()}
                </div>
                <div className="overflow-hidden flex-1">
                <p className="text-sm font-bold truncate text-slate-800 dark:text-slate-200">{user?.username}</p>
                <p className="text-xs text-slate-500 truncate capitalize">{user?.role?.toLowerCase()}</p>
                </div>
                <button 
                    onClick={handleLogout}
                    title="Sign Out"
                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                >
                    <LogOut size={18} />
                </button>
            </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-950 relative">
        <header className="sticky top-0 z-20 h-20 flex items-center px-8 justify-between backdrop-blur-md bg-white/70 dark:bg-slate-950/70 border-b border-slate-200/50 dark:border-slate-800/50 transition-colors duration-300">
            <div>
                <h2 className="text-2xl font-bold text-slate-800 dark:text-white">
                    {location.pathname === '/' ? 'Asset Library' : 
                    location.pathname.startsWith('/rooms') ? 'Virtual Rooms' : 
                    'Dashboard'}
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                    Manage and organize your digital assets
                </p>
            </div>
        </header>
        
        <div className="p-8 max-w-7xl mx-auto">
            <AnimatePresence mode='wait'>
                <motion.div
                    key={location.pathname}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                >
                    <Outlet />
                </motion.div>
            </AnimatePresence>
        </div>
      </main>
    </div>
  );
};
