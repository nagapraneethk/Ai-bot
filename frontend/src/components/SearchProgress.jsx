import { useState, useEffect } from 'react';

export const SearchProgress = ({ query, college }) => {
  const [steps, setSteps] = useState([]);
  
  useEffect(() => {
    // Reset steps when query changes
    setSteps([]);
    
    // Define steps based on context (initial search vs college specific)
    let progressSteps = [];
    
    if (college) {
      // Specific college search steps - matching our new robust backend logic
      progressSteps = [
        { text: `Analyzing question intent...`, delay: 0 },
        { text: `Scanning ${college.domain || 'official website'} for official data...`, delay: 1000 },
        { text: `Cross-referencing: Checking Shiksha.com for ${college.name}...`, delay: 3000 },
        { text: `Cross-referencing: Checking Collegedunia.com...`, delay: 4500 },
        { text: `Cross-referencing: Checking Careers360.com...`, delay: 6000 },
        { text: 'Verifying data accuracy...', delay: 7500 },
        { text: 'Synthesizing comprehensive answer...', delay: 9000 }
      ];
    } else {
      // General search steps
      progressSteps = [
        { text: `Searching for "${query}"...`, delay: 0 },
        { text: 'Identifying official sources...', delay: 2000 },
        { text: 'Analyzing results...', delay: 4000 }
      ];
    }

    let timeouts = [];

    progressSteps.forEach((step) => {
      const timeout = setTimeout(() => {
        setSteps(prev => {
          // Keep only the last 3 steps to prevent overcrowding if we had more
          const newSteps = [...prev, step.text];
          return newSteps.slice(-3);
        });
      }, step.delay);
      timeouts.push(timeout);
    });

    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, [query, college]);

  return (
    <div className="flex flex-col gap-3 w-full max-w-2xl animate-fade-in my-4 pl-4">
      <div className="flex flex-col gap-2">
        {steps.map((text, index) => (
          <div key={index} className="flex items-center gap-3 text-sm animate-fade-in">
            {index === steps.length - 1 ? (
              // Active step
              <>
                <div className="w-4 h-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin flex-shrink-0 shadow-lg shadow-indigo-500/50"></div>
                <span className="text-slate-200 font-medium tracking-wide">{text}</span>
              </>
            ) : (
              // Completed step
              <>
                <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
                  <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-slate-500 line-through decoration-indigo-500/30">{text}</span>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
