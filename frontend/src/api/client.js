// API client for college enquiry chatbot

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Resolve college name to find official websites
 * @param {string} collegeName - Name of the college
 * @param {boolean} forceSearch - If true, skip known colleges and search the web
 */
export async function resolveCollege(collegeName, forceSearch = false) {
    const response = await fetch(`${API_URL}/college/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            college_name: collegeName,
            force_search: forceSearch
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to find college');
    }

    return response.json();
}

/**
 * Confirm a college and trigger scraping
 */
export async function confirmCollege(url, collegeName) {
    const response = await fetch(`${API_URL}/college/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, college_name: collegeName }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to confirm college');
    }

    return response.json();
}

/**
 * Send a chat message about the college
 */
export async function sendChatMessage(collegeId, question) {
    const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ college_id: collegeId, question }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get answer');
    }

    return response.json();
}

/**
 * Get college info by ID
 */
export async function getCollegeInfo(collegeId) {
    const response = await fetch(`${API_URL}/college/${collegeId}`);

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'College not found');
    }

    return response.json();
}
