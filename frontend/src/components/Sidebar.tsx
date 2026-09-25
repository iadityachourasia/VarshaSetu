import React from 'react';
import { 
  CloudRain, BarChart3, ShieldCheck, Cpu, Sliders, 
  Layers, Compass, LogOut, LogIn, ChevronRight
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  user: { name: string; email: string; role: string } | null;
  onOpenAuth: (mode: 'login' | 'register') => void;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  user,
  onOpenAuth,
  onLogout
}) => {
  const groups = [
    {
      title: 'OPERATIONAL & FORECAST',
      items: [
        { id: 'forecast', label: 'Historical Replay (Blocked)', icon: CloudRain },
        { id: 'verification', label: 'Verification & Skill', icon: BarChart3 },
      ]
    },
    {
      title: 'ANALYTICS & INTELLIGENCE',
      items: [
        { id: 'regimes', label: 'Regime Intelligence', icon: Layers },
        { id: 'ablation', label: 'Ablation & Models', icon: Cpu },
        { id: 'features', label: 'Feature Importance', icon: Compass },
        { id: 'calibration', label: 'Probability Calibration', icon: ShieldCheck },
      ]
    },
    {
      title: 'TOOLS & SANDBOX',
      items: [
        { id: 'sandbox', label: 'Model Sandbox', icon: Sliders },
      ]
    }
  ];

  return (
    <aside className="w-[260px] min-w-[260px] bg-gradient-to-b from-[#0B1220] via-[#0E162B] to-[#111B35] text-white min-h-screen flex flex-col justify-between p-4 border-r border-[#94a3b8]/20 backdrop-blur-[20px] shadow-2xl z-30 flex-shrink-0">
      <div className="space-y-6">
        
        {/* VarshaSetu Brand Header */}
        <div className="flex items-center space-x-3 px-2 py-4 border-b border-slate-800/80">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30 flex-shrink-0">
            <CloudRain className="w-6 h-6" />
          </div>
          <div className="overflow-hidden">
            <div className="flex items-center space-x-1.5">
              <span className="font-black text-xl tracking-tight text-white leading-none">VarshaSetu</span>
              <span className="bg-indigo-950/90 text-indigo-300 text-[10px] font-black px-1.5 py-0.5 rounded border border-indigo-700/60 shrink-0">
                SIH26080
              </span>
            </div>
            <p className="text-xs text-slate-400 font-bold mt-1">Scientific Prototype</p>
          </div>
        </div>

        {/* Navigation Categories */}
        <nav className="space-y-6">
          {groups.map((group, idx) => (
            <div key={idx} className="space-y-2">
              <span className="px-3 text-xs font-black tracking-wider text-slate-400 uppercase block">
                {group.title}
              </span>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      className={`w-full flex items-center justify-between px-3.5 h-[46px] text-[15px] font-bold rounded-xl transition-all duration-200 relative cursor-pointer ${
                        isActive
                          ? 'bg-gradient-to-r from-indigo-600/90 to-blue-600/90 text-white shadow-md shadow-indigo-500/20 border border-indigo-400/40 font-extrabold'
                          : 'text-slate-200 hover:text-white hover:bg-slate-800/60'
                      }`}
                    >
                      <div className="flex items-center space-x-3 truncate">
                        <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                        <span className="truncate">{item.label}</span>
                      </div>
                      {isActive && <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] shrink-0"></div>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* User Profile Card */}
      <div className="pt-4 border-t border-slate-800">
        {user ? (
          <div className="bg-slate-900/90 rounded-xl p-3 flex items-center justify-between border border-slate-800 shadow-inner">
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center text-white font-black text-base shadow-md flex-shrink-0">
                {user.name.charAt(0)}
              </div>
              <div className="truncate text-left">
                <div className="text-xs font-extrabold text-white truncate">{user.name}</div>
                <div className="text-[11px] text-slate-300 font-semibold truncate">{user.email}</div>
              </div>
            </div>
            <button
              onClick={onLogout}
              title="Sign Out"
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-all ml-1 cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => onOpenAuth('login')}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white h-[46px] px-3.5 rounded-xl flex items-center justify-between text-xs font-black transition-all shadow-md cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <LogIn className="w-4 h-4 text-emerald-400" />
              <span>Authentication unavailable</span>
            </div>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </aside>
  );
};
