/**
 * Modal for confirming college website selection
 */
export function CollegeConfirmModal({ 
  isOpen, 
  candidates, 
  collegeName,
  onConfirm, 
  onCancel,
  onSearchWeb
}) {
  if (!isOpen) return null;
  
  const getConfidenceBadge = (confidence) => {
    const styles = {
      high: 'bg-green-500/10 text-green-400 border-green-500/20',
      medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      low: 'bg-red-500/10 text-red-400 border-red-500/20'
    };
    return styles[confidence] || styles.low;
  };
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onCancel}
      ></div>
      
      {/* Modal */}
      <div className="relative bg-[#212121] border border-gray-700 rounded-xl p-6 max-w-lg w-full animate-slide-in shadow-2xl">
        <h3 className="text-xl font-semibold text-gray-100 mb-2">
          Confirm College Website
        </h3>
        <p className="text-gray-400 text-sm mb-6">
          Select the official website for <span className="text-white font-medium">{collegeName}</span>
        </p>
        
        <div className="space-y-3 mb-6">
          {candidates.map((candidate, index) => (
            <button
              key={index}
              onClick={() => onConfirm(candidate)}
              className="w-full text-left p-4 rounded-xl bg-[#2f2f2f] hover:bg-[#383838] border border-gray-700 hover:border-gray-500 transition-all group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-gray-200 font-medium text-sm truncate group-hover:text-white transition-colors">
                    {candidate.name}
                  </p>
                  <p className="text-gray-500 text-xs mt-1 truncate">
                    {candidate.url}
                  </p>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full border ${getConfidenceBadge(candidate.confidence)}`}>
                  {candidate.confidence}
                </span>
              </div>
            </button>
          ))}
        </div>
        
        {/* Not these? Button */}
        <button
          onClick={onSearchWeb}
          className="w-full py-3 mb-2 text-sm text-teal-400 hover:text-teal-300 hover:bg-teal-500/10 rounded-lg transition-all flex items-center justify-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Not these? Search the web
        </button>
        
        <button
          onClick={onCancel}
          className="w-full py-3 text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
