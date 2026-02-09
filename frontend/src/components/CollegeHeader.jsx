/**
 * Header showing currently selected college with reset option
 */
export function CollegeHeader({ college, onReset }) {
  if (!college) return null;
  
  return (
    <div className="bg-slate-900 border border-slate-800/80 rounded-2xl px-5 py-4 flex items-center justify-between animate-slide-in mb-6 shadow-xl shadow-black/20">
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="w-3 h-3 bg-emerald-500 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.4)]"></div>
          <div className="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-20"></div>
        </div>
        <div>
          <h2 className="text-slate-100 font-semibold text-sm md:text-base tracking-wide">
            {college.name}
          </h2>
          <p className="text-slate-400 text-xs font-medium mt-0.5 flex items-center gap-2">
            <span className="text-indigo-400">{college.domain}</span>
            <span className="w-1 h-1 rounded-full bg-slate-600"></span>
            <span>{college.pagesCount} pages knowledge base</span>
          </p>
        </div>
      </div>
      <button
        onClick={onReset}
        className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 hover:text-white hover:border-indigo-500/30 transition-all duration-200 shadow-sm"
      >
        Change
      </button>
    </div>
  );
}
