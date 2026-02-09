import { useState, useEffect } from 'react';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [displayedText, setDisplayedText] = useState(isUser ? message.content : '');
  const [isTyping, setIsTyping] = useState(!isUser);

  useEffect(() => {
    if (isUser || !message.content) {
      setDisplayedText(message.content || '');
      setIsTyping(false);
      return;
    }

    // Standard typewriter effect using slicing to ensure no dropped chars
    setDisplayedText('');
    setIsTyping(true);
    
    let currentIndex = 0;
    const text = message.content;
    const speed = 10; 

    // Clear any previous interval if effect re-runs
    const interval = setInterval(() => {
      currentIndex++;
      setDisplayedText(text.slice(0, currentIndex));
      
      if (currentIndex >= text.length) {
        setIsTyping(false);
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [message.content, isUser]);

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in group`}>
      {!isUser && (
        <div className="flex-shrink-0 mr-4 mt-1">
          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center border border-slate-700">
            <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
      )}
      
      <div
        className={`relative max-w-[85%] md:max-w-[70%] ${
          isUser
            ? 'bg-slate-800 text-white px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-lg'
            : 'text-slate-200 pr-4'
        }`}
      >
        <div className="text-base md:text-lg leading-7 md:leading-8 font-mono md:font-sans markdown-body">
          {isUser ? (
            <div className="whitespace-pre-wrap font-medium">{displayedText}</div>
          ) : (
             <ReactMarkdown 
               remarkPlugins={[remarkGfm]}
               components={{
                 ul: ({node, ...props}) => <ul className="list-disc pl-4 my-2 space-y-1 text-slate-300" {...props} />,
                 ol: ({node, ...props}) => <ol className="list-decimal pl-4 my-2 space-y-1 text-slate-300" {...props} />,
                 li: ({node, ...props}) => <li className="mb-0.5" {...props} />,
                 p: ({node, ...props}) => <p className="mb-2 last:mb-0 inline-block text-slate-200" {...props} />,
                 strong: ({node, ...props}) => <strong className="font-bold text-slate-100" {...props} />,
                 a: ({node, ...props}) => <a className="text-cyan-400 hover:text-cyan-300 hover:underline transition-colors" {...props} />,
                 code: ({node, inline, ...props}) => (
                    inline 
                      ? <code className="bg-slate-800 text-slate-200 px-1 py-0.5 rounded text-sm font-mono border border-slate-700/50" {...props} />
                      : <code className="block bg-slate-900 p-3 rounded-lg text-sm font-mono my-2 border border-slate-800 overflow-x-auto" {...props} />
                 ),
                 blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-slate-700 pl-4 py-2 my-4 italic text-slate-400 font-serif" {...props} />
               }}
             >
               {displayedText}
             </ReactMarkdown>
          )}
          {isTyping && <span className="animate-pulse inline-block w-1.5 h-5 ml-1 bg-cyan-500 align-text-bottom rounded-full opacity-70"></span>}
        </div>
        
        {(message.sources && message.sources.length > 0) ? (
          <div className="mt-4 flex flex-col gap-2 border-t border-slate-800/60 pt-3">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Sources Used</div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, idx) => (
                <a 
                  key={idx}
                  href={source.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-400 hover:bg-slate-800 hover:text-cyan-400 hover:border-cyan-500/30 transition-all duration-200 group/source"
                >
                  <span className="font-medium">{source.type.replace('_aggregator', '')}</span>
                  <svg className="w-3 h-3 opacity-60 group-hover/source:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              ))}
            </div>
          </div>
        ) : message.sourcePage && (
          <div className="mt-4 flex flex-col gap-2 border-t border-slate-800/60 pt-3">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Source</div>
            {message.sourceUrl ? (
              <a 
                href={message.sourceUrl} 
                target="_blank" 
                rel="noopener noreferrer" 
                 className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-400 hover:bg-slate-800 hover:text-cyan-400 hover:border-cyan-500/30 transition-all duration-200 group/source w-fit"
              >
                <span>{message.sourcePage}</span>
                <svg className="w-3 h-3 opacity-60 group-hover/source:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            ) : (
              <span className="px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-400 w-fit">
                {message.sourcePage}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
