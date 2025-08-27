import { useState, useEffect } from 'react';
import { useImmer } from 'use-immer';
import api from '../../api';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';


function Chatbot() {
    const [messages, setMessages] = useImmer([]);
    const [newMessage, setNewMessage] = useState('');
    const [isPolling, setIsPolling] = useState(false);
    const [conversationState, setConversationState] = useState(null); // Track conversation state

    const isLoading = isPolling;

    const getTimeBasedGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning!';
        if (hour < 18) return 'Good afternoon!';
        return 'Good evening!';
    };

    const submitNewMessage = async () => {
        const trimmedMessage = newMessage.trim();
        if (!trimmedMessage || isPolling) return;

        console.log(`User Message in Chatbot.jsx: ${trimmedMessage}`);
        // Show user message and assistant placeholder
        setMessages(draft => [
        ...draft,
        { role: 'user', content: trimmedMessage },
        { role: 'assistant', content: 'Processing your query...', loading: true }
        ]);
        setNewMessage('');

        try {
        let response;

        if (conversationState) {
            // Follow-up: call /continue
            response = await api.continuePipeline(trimmedMessage, conversationState);
            console.log(`Follow-up Response from /continue: ${JSON.stringify(response)}`);
        } else {
            // Initial query: call /start
            response = await api.startPipeline(trimmedMessage);
            console.log(`Initial Response from /start: ${JSON.stringify(response)}`);
        }

        // Store and log conversation state
        if (response.state) {
            setConversationState(response.state);
            console.log("Updated Conversation State (on submit):", response.state); // log state
        }

        setIsPolling(true);
        } catch (err) {
        console.error(err);
        setMessages(draft => {
            draft[draft.length - 1] = {
            role: 'assistant',
            content: 'Something went wrong while processing your query.',
            loading: false
            };
        });
        }
    };

    // Poll status every 2s
    useEffect(() => {
        if (!isPolling) return;

        const interval = setInterval(async () => {
        try {
            const status = await api.getPipelineStatus();
            console.log(`Status from /status: ${JSON.stringify(status)}`);

            // Save and log updated state
            if (status.state) {
            setConversationState(status.state);
            console.log("Updated Conversation State (on polling):", status.state); // log state
            }

            setMessages(draft => {
            const last = draft[draft.length - 1];
            if (status.stage === 'COMPLETED' && status.results) {
                console.log(`Results: ${JSON.stringify(status.results)}`);
                const formattedContent = Object.entries(status.results)
                .map(([tool, result]) => {
                const explanation = typeof result === 'string' ? result : result.output_text;
                return `### Tool used for the query: ${tool}\n\n${explanation}`;
                })
                .join('\n\n');

                draft[draft.length - 1] = {
                role: 'assistant',
                content: formattedContent,
                loading: false
                };
                setIsPolling(false);
                clearInterval(interval);
            } else {
                last.content = `Current stage: ${status.stage}`;
            }
            });
        } catch (err) {
            console.error('Error polling pipeline:', err);
            setMessages(draft => {
            draft[draft.length - 1] = {
                role: 'assistant',
                content: 'Error checking pipeline status.',
                loading: false
            };
            });
            setIsPolling(false);
            clearInterval(interval);
        }
        }, 2000);

        return () => clearInterval(interval);
    }, [isPolling]);

    return (
        <div className='relative grow flex flex-col gap-6 pt-6'>
        {messages.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
            <p className="font-urbanist text-4xl font-semibold text-[#8F8F8F] text-center px-4">
                Hello there, {getTimeBasedGreeting()}
            </p>
            </div>
        )}

        <ChatMessages messages={messages} isLoading={isLoading} />
        <ChatInput
            newMessage={newMessage}
            isLoading={isLoading}
            setNewMessage={setNewMessage}
            submitNewMessage={submitNewMessage}
        />
        </div>
    );
}

export default Chatbot;