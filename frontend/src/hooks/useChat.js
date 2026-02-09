import { useState, useCallback } from 'react';
import { resolveCollege, confirmCollege, sendChatMessage } from '../api/client';

/**
 * Custom hook for managing chat state and API calls
 */
export function useChat() {
    const [messages, setMessages] = useState([]);
    const [college, setCollege] = useState(null);
    const [candidates, setCandidates] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [pendingCollegeName, setPendingCollegeName] = useState('');
    const [error, setError] = useState(null);

    // Add a message to the chat
    const addMessage = useCallback((role, content, extra = {}) => {
        setMessages(prev => [...prev, {
            id: Date.now(),
            role,
            content,
            timestamp: new Date(),
            ...extra
        }]);
    }, []);

    // Handle user sending a message
    const sendMessage = useCallback(async (text) => {
        if (!text.trim()) return;

        setError(null);
        addMessage('user', text);

        // If no college selected, try to resolve
        if (!college) {
            setIsLoading(true);
            setPendingCollegeName(text);

            try {
                const result = await resolveCollege(text);
                setCandidates(result.candidates);
                setShowConfirmModal(true);
                addMessage('assistant', `I found ${result.candidates.length} possible website(s) for "${text}". Please confirm the correct one.`);
            } catch (err) {
                addMessage('assistant', `Sorry, I couldn't find an official website for "${text}". Please try a different name or spelling.`);
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
            return;
        }

        // College is selected, send chat message
        setIsLoading(true);
        try {
            const result = await sendChatMessage(college.id, text);
            addMessage('assistant', result.answer, {
                sourcePage: result.source_page,
                sourceUrl: result.source_url
            });
        } catch (err) {
            addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [college, addMessage]);

    // Handle college confirmation
    const handleConfirmCollege = useCallback(async (candidate) => {
        setShowConfirmModal(false);
        setIsLoading(true);
        addMessage('assistant', `Scraping data from ${candidate.url}... This may take a minute.`);

        try {
            const result = await confirmCollege(candidate.url, pendingCollegeName);
            setCollege({
                id: result.college_id,
                name: pendingCollegeName,
                domain: candidate.url,
                pagesCount: result.pages_count
            });
            addMessage('assistant', `${result.message}\n\nYou can now ask me anything about ${pendingCollegeName}!`);
            setCandidates([]);
        } catch (err) {
            addMessage('assistant', `Failed to scrape the website: ${err.message}`);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [pendingCollegeName, addMessage]);

    // Cancel college selection
    const handleCancelConfirm = useCallback(() => {
        setShowConfirmModal(false);
        setCandidates([]);
        addMessage('assistant', 'Selection cancelled. Please enter a college name to try again.');
    }, [addMessage]);

    // Search the web for the college (when user clicks "Not these?")
    const handleSearchWeb = useCallback(async () => {
        setShowConfirmModal(false);
        setCandidates([]);
        setIsLoading(true);
        addMessage('assistant', `Searching the web for "${pendingCollegeName}"... This may take a moment.`);

        try {
            const result = await resolveCollege(pendingCollegeName, true); // force web search
            setCandidates(result.candidates);
            setShowConfirmModal(true);
            addMessage('assistant', `Found ${result.candidates.length} result(s) from web search. Please select the correct one.`);
        } catch (err) {
            addMessage('assistant', `Sorry, I couldn't find "${pendingCollegeName}" on the web either. Please check the spelling or try a different name.`);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [pendingCollegeName, addMessage]);

    // Reset and select different college
    const resetCollege = useCallback(() => {
        setCollege(null);
        setMessages([]);
        setCandidates([]);
        setError(null);
        setShowConfirmModal(false);
    }, []);

    return {
        messages,
        college,
        candidates,
        isLoading,
        showConfirmModal,
        error,
        sendMessage,
        handleConfirmCollege,
        handleCancelConfirm,
        handleSearchWeb,
        resetCollege,
    };
}
