import { useRef, useEffect, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { CollegeHeader } from './CollegeHeader';
import { CollegeConfirmModal } from './CollegeConfirmModal';
import { useChat } from '../hooks/useChat';
import { SearchProgress } from './SearchProgress';

/**
 * Main chat interface component
 */
export function ChatInterface() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  
  const {
    messages,
    college,
    candidates,
    isLoading,
    showConfirmModal,
    sendMessage,
    handleConfirmCollege,
    handleCancelConfirm,
    handleSearchWeb,
    resetCollege,
  } = useChat();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="h-screen flex flex-col w-full font-sans text-slate-200 overflow-hidden bg-slate-950 selection:bg-indigo-500/30">
      {/* Header - Fixed at top */}
      <header className="py-5 px-6 flex-shrink-0 z-10 bg-slate-950 border-b border-slate-800/60">
        <div className="max-w-4xl mx-auto flex items-center justify-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-900/20">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18 18.246 18.477 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div className="text-left">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              UniScout <span className="text-indigo-500 font-medium">AI</span>
            </h1>
            <p className="text-slate-500 text-xs font-medium uppercase tracking-widest">
              {college 
                ? `Exploring ${college.name}` 
                : 'Intelligence for Education'}
            </p>
          </div>
        </div>
      </header>

      {/* College header (if selected) */}
      <div className="px-4 flex-shrink-0 mt-4">
        <div className="max-w-4xl mx-auto">
          <CollegeHeader college={college} onReset={resetCollege} />
        </div>
      </div>

      {/* Chat messages - Scrollable Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 scroll-smooth scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
        <div className="max-w-4xl mx-auto space-y-8">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 flex flex-col items-center justify-center h-full min-h-[50vh] animate-fade-in">
              <div className="w-20 h-20 mb-8 rounded-3xl bg-slate-900 border border-slate-800 flex items-center justify-center shadow-2xl">
                 <svg className="w-10 h-10 text-indigo-500 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                 </svg>
              </div>
              <p className="text-2xl font-bold text-slate-200">Where are we headed?</p>
              <p className="text-slate-500 mt-4 text-sm max-w-sm mx-auto leading-relaxed">
                Enter any college name to begin scouting admission data, placement stats, and more.
              </p>
              <div className="mt-8 flex gap-3 flex-wrap justify-center">
                {['IIT Bombay', 'VIT Vellore', 'MIT Manipal'].map(c => (
                  <button 
                    key={c}
                    onClick={() => setInput(c)}
                    className="px-4 py-2 rounded-full bg-slate-900 border border-slate-800 text-xs font-medium text-slate-400 hover:text-indigo-400 hover:border-indigo-500/30 transition-all"
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          
          {isLoading && (
            <div className="flex justify-start animate-fade-in w-full pb-4">
               <SearchProgress query={input.trim() || 'College Search'} college={college} />
            </div>
          )}
          
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>

      {/* Input form - Fixed at bottom */}
      <div className="p-6 flex-shrink-0 bg-slate-950 border-t border-slate-900/50">
        <div className="max-w-4xl mx-auto w-full">
          <form onSubmit={handleSubmit} className="mb-3">
            <div className="relative">
              <div className="input-container flex gap-2 items-center bg-slate-900 rounded-2xl border border-slate-800 focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/10 transition-all duration-200 shadow-lg">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={college ? 'Ask anything about admission, fees, or placements...' : 'Enter a college name...'}
                  disabled={isLoading}
                  className="flex-1 bg-transparent border-none text-slate-200 px-6 py-4.5 placeholder-slate-600 focus:outline-none text-base w-full"
                />
                <div className="pr-3">
                  <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className={`p-3 rounded-xl transition-all duration-200 flex items-center justify-center ${
                      !input.trim() || isLoading 
                        ? 'text-slate-600 cursor-not-allowed bg-transparent' 
                        : 'bg-indigo-600 text-white hover:bg-indigo-500 active:scale-95'
                    }`}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </form>

          {/* Footer */}
          <div className="flex items-center justify-center gap-6 text-[10px] text-slate-600 font-bold uppercase tracking-[0.2em]">
            <span>Secured Sources</span>
            <span className="w-1 h-1 rounded-full bg-slate-800"></span>
            <span>Real-time Scrape</span>
            <span className="w-1 h-1 rounded-full bg-slate-800"></span>
            <span>AI Verified</span>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <CollegeConfirmModal
        isOpen={showConfirmModal}
        candidates={candidates}
        collegeName={input || 'this college'}
        onConfirm={handleConfirmCollege}
        onCancel={handleCancelConfirm}
        onSearchWeb={handleSearchWeb}
      />
    </div>
  );
}
