import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserRole } from '../types';
import api from '../api/client';
import { Lock, User, Box, ArrowRight, ShieldCheck, GraduationCap } from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>(UserRole.STUDENT);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await api.post('/auth/register', { username, password, role });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-6 relative overflow-hidden">
        {/* Background Decor */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden">
            <img 
                src="/assets/login-bg.png" 
                alt="VR Education Background" 
                className="w-full h-full object-cover opacity-30 dark:opacity-40 blur-sm"
            />
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 mix-blend-overlay"></div>
        </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl relative z-10"
      >
        <div className="flex justify-center mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-xl shadow-indigo-500/20">
                <Box size={30} className="text-white" />
            </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl shadow-indigo-500/5">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Create Account</h1>
                <p className="text-slate-500 dark:text-slate-400">Join the virtual classroom experience</p>
            </div>

            {error && (
            <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-400 p-3 rounded-xl mb-6 text-sm text-center font-medium"
            >
                {error}
            </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
            <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">I am a...</label>
                <div className="grid grid-cols-2 gap-4">
                <div 
                    onClick={() => setRole(UserRole.STUDENT)}
                    className={clsx(
                    "cursor-pointer p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2",
                    role === UserRole.STUDENT 
                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" 
                        : "border-slate-200 dark:border-slate-800 hover:border-indigo-200 dark:hover:border-slate-700 text-slate-500 dark:text-slate-400"
                    )}
                >
                    <GraduationCap size={24} />
                    <span className="font-medium text-sm">Student</span>
                </div>
                <div 
                    onClick={() => setRole(UserRole.STAFF)}
                    className={clsx(
                    "cursor-pointer p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2",
                    role === UserRole.STAFF 
                        ? "border-purple-500 bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400" 
                        : "border-slate-200 dark:border-slate-800 hover:border-purple-200 dark:hover:border-slate-700 text-slate-500 dark:text-slate-400"
                    )}
                >
                    <ShieldCheck size={24} />
                    <span className="font-medium text-sm">Staff</span>
                </div>
                </div>
            </div>

            <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Username</label>
                <div className="relative group">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors" size={20} />
                <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3.5 pl-12 pr-4 text-slate-900 dark:text-slate-100 font-medium focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all placeholder:text-slate-400"
                    placeholder="Enter your username"
                    required
                />
                </div>
            </div>

            <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Password</label>
                <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors" size={20} />
                <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3.5 pl-12 pr-4 text-slate-900 dark:text-slate-100 font-medium focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all placeholder:text-slate-400"
                    placeholder="Choose a password"
                    required
                />
                </div>
            </div>

            <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
            >
                {loading ? 'Creating Account...' : 'Create Account'}
                {!loading && <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />}
            </button>
            </form>

            <div className="mt-8 text-center text-sm">
            <span className="text-slate-500 dark:text-slate-400">Already have an account? </span>
            <Link to="/login" className="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold">
                Sign In
            </Link>
            </div>
        </div>
      </motion.div>
    </div>
  );
};
