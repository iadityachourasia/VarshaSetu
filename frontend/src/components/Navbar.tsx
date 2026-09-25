import React from 'react';
import { Search, Bell, Settings, ShieldCheck, Filter, Sliders, BarChart2 } from 'lucide-react';

interface NavbarProps {
  sha256Hash?: string;
  activeFilterTab: string;
  setActiveFilterTab: (filter: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  onOpenNotifications: () => void;
  onOpenSettings: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  sha256Hash,
  activeFilterTab,
  setActiveFilterTab,
  searchQuery,
  setSearchQuery,
  onOpenNotifications,
  onOpenSettings
}) => {
  return (
    <header className="bg-white/95 backdrop-blur-md border-b border-slate-300 sticky top-0 z-20 px-8 py-5 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        {/* LEFT: Clean Scientific Title */}
        <div>
          <h1 className="text-3xl lg:text-4xl font-black text-slate-950 tracking-tight">
            VarshaSetu Scientific Prototype
          </h1>
          <p className="text-sm lg:text-base font-bold text-slate-700 mt-1">
            Phase 0 stabilization — current scientific outputs unavailable
          </p>
        </div>

        {/* CENTER/RIGHT: Search + Dataset SHA-256 + Notifications + Settings */}
        <div className="flex items-center space-x-3 shrink-0">
          
          {/* Search Box */}
          <div className="relative">
            <Search className="w-5 h-5 text-slate-600 absolute left-3.5 top-3.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search parameters or data..."
              className="bg-slate-50 border border-slate-300 text-slate-950 placeholder-slate-500 text-sm lg:text-base font-bold rounded-[12px] pl-11 pr-8 h-[46px] w-64 lg:w-80 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 focus:bg-white transition-all shadow-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-3.5 text-xs text-slate-500 hover:text-slate-900 font-extrabold"
              >
                ✕
              </button>
            )}
          </div>

          {/* Dataset SHA-256 Component */}
          <div 
            title={sha256Hash || 'Dataset SHA-256 Integrity Hash'}
            className="hidden xl:flex items-center space-x-2 bg-slate-950 text-white text-xs lg:text-sm px-4 h-[46px] rounded-[12px] border border-slate-800 shadow-sm cursor-default"
          >
            <span className="text-slate-400 font-mono font-bold text-xs">Dataset SHA-256</span>
            <code className="text-emerald-400 font-mono text-xs font-black tracking-wider">
              {sha256Hash ? (sha256Hash.length > 16 ? `${sha256Hash.substring(0, 16)}...` : sha256Hash) : '3e04df58e8b84e13...'}
            </code>
          </div>

          {/* Notifications Button */}
          <button 
            onClick={onOpenNotifications}
            title="Notifications & System Alerts"
            className="h-[46px] w-[46px] flex items-center justify-center text-slate-800 hover:text-slate-950 bg-slate-100 hover:bg-slate-200 rounded-[12px] border border-slate-300 relative transition-all shadow-sm cursor-pointer"
          >
            <Bell className="w-5 h-5" />
            <span className="w-2.5 h-2.5 bg-rose-600 rounded-full absolute top-3 right-3 ring-2 ring-white animate-pulse"></span>
          </button>

          {/* Settings Button */}
          <button 
            onClick={onOpenSettings}
            title="Settings & Display Options"
            className="h-[46px] w-[46px] flex items-center justify-center text-white bg-slate-950 hover:bg-slate-800 rounded-[12px] shadow-sm transition-all cursor-pointer"
          >
            <Settings className="w-5 h-5" />
          </button>

        </div>
      </div>

      {/* Navigation Sub-Tab Bar */}
      <div className="flex items-center space-x-2 mt-5 pt-3 border-t border-slate-200 overflow-x-auto scrollbar-none">
        {[
          { id: 'value', label: 'Value comparison', icon: BarChart2 },
          { id: 'average', label: 'Average values', icon: Filter },
          { id: 'configure', label: 'Configure analysis', icon: Sliders },
          { id: 'filter', label: 'Filter analysis', icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeFilterTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveFilterTab(tab.id)}
              className={`flex items-center gap-2.5 h-[48px] px-5 text-[15px] font-extrabold transition-all border-b-2 whitespace-nowrap rounded-t-xl cursor-pointer ${
                isActive
                  ? 'border-indigo-600 text-indigo-950 font-black bg-indigo-50/80 shadow-sm'
                  : 'border-transparent text-slate-700 hover:text-slate-950 hover:bg-slate-100/80'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-indigo-600' : 'text-slate-600'}`} />
              <span>{tab.label}</span>
              {isActive && (
                <span className="w-2 h-2 rounded-full bg-indigo-600 ml-1"></span>
              )}
            </button>
          );
        })}
      </div>
    </header>
  );
};
