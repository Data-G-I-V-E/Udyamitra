const BASE_URL = "http://localhost:8000";   

// Start the pipeline
async function startPipeline(userQuery) {
    console.log(`userQuery: ${userQuery}`);
    const res = await fetch(BASE_URL + '/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_query: userQuery })
    });

    const data = await res.json();

    if (!res.ok) {
        throw new Error(data.detail || 'Pipeline start failed');
    }

    console.log(data);
    return data;
}

// Continue the pipeline with chat memory
async function continuePipeline(userQuery, conversationState) {
    const res = await fetch(BASE_URL + '/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
        user_query: userQuery,
        conversation_state: conversationState
        })
    });

    const data = await res.json();

    if (!res.ok) {
        throw new Error(data.detail || 'Pipeline continuation failed');
    }

    console.log(data);
    return data;
}

// Poll the pipeline status
async function getPipelineStatus() {
    const res = await fetch(BASE_URL + '/status');

    const data = await res.json();

    if (!res.ok) {
        throw new Error(data.detail || 'Status fetch failed');
    }

    console.log(data);
    return data;
}

export default {
    startPipeline,
    continuePipeline,
    getPipelineStatus
};