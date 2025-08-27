import Markdown from 'react-markdown';
import useAutoScroll from '../../hooks/useAutoScroll';
import Spinner from '../chat/Spinner';

function ChatMessages({ messages, isLoading }) {
    const scrollContentRef = useAutoScroll(isLoading);

    return (
        <div
        ref={scrollContentRef}
        className="grow space-y-4 px-2 overflow-y-auto"
        >
            {messages.map(({ role, content, loading, error }, idx) => {
            const isUser = role === 'user';

            // Row container: push user rows to the right
            const rowClass = isUser
            ? 'flex w-full justify-end'
            : 'flex w-full justify-start';

            // Bubble styles
            // Bubble styles
            const bubbleBase =
            'rounded-xl px-4 py-3 shadow-sm max-w-[80%] whitespace-pre-wrap text-left'; 
            const bubbleClass = isUser
            ? `${bubbleBase} bg-[#DEDEDE]`
            : `${bubbleBase} bg-[#FFFFFF] border border-gray-200`;

            // Optional layout for avatar (kept but not required)
            const innerLayout = isUser
            ? 'flex items-start gap-3 flex-row-reverse'
            : 'flex items-start gap-3';

            return (
            <div key={idx} className={rowClass}>
                <div className={innerLayout}>
                {/* Optional avatar slot */}
                {/* {isUser ? (
                    <img className="h-6 w-6 shrink-0 rounded-full" src={userIcon} alt="user" />
                ) : (
                    <img className="h-6 w-6 shrink-0 rounded-full" src={botIcon} alt="assistant" />
                )} */}

                <div className={bubbleClass}>
                    <div className="markdown-container">
                    {loading && !content ? (
                        <Spinner />
                    ) : !isUser ? (
                        // Assistant/tool output (Markdown + tool-object support)
                        <Markdown
                        components={{
                            p: ({ children }) => (
                            <p className="whitespace-pre-line">{children}</p>
                            ),
                        }}
                        >
                        {typeof content === 'string'
                            ? content
                            : Object.entries(content || {})
                                .map(
                                ([tool, explanation]) =>
                                    `### Tool: ${tool}\n\n${explanation}`
                                )
                                .join('\n\n')}
                        </Markdown>
                    ) : (
                        // User content (plain text)
                        <div className="whitespace-pre-line">
                        {typeof content === 'string'
                            ? content
                            : JSON.stringify(content, null, 2)}
                        </div>
                    )}
                    </div>

                    {error && (
                    <div
                        className={`flex items-center gap-1 text-sm text-red-600 mt-2`}
                    >
                        {/* <img className="h-5 w-5" src={errorIcon} alt="error" /> */}
                        <span>Error generating the response</span>
                    </div>
                    )}
                </div>
                </div>
            </div>
            );
        })}
        </div>
    );
}

export default ChatMessages;