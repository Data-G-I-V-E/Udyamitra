import useAutosize from "../../hooks/useAutosize";
import { Paperclip, Send, Mic } from "lucide-react"; // modern icons

function ChatInput({ newMessage, isLoading, setNewMessage, submitNewMessage }) {
    const textareaRef = useAutosize(newMessage);

    function handleKeyDown(e) {
        if (e.keyCode === 13 && !e.shiftKey && !isLoading) {
            e.preventDefault();
            submitNewMessage();
        }
    }

    return (
        <div className="sticky bottom-0 shrink-0 py-6">
            <div className="flex items-center bg-gray-100 relative rounded-3xl ring-gray-300 ring-1 focus-within:ring-2 transition-all px-2">
                
                {/* + Attach button (left side) */}
                <button
                    className="p-2 rounded-full hover:bg-gray-200 text-gray-600"
                    title="Attach file"
                >
                    <Paperclip size={20} />
                </button>

                {/* Textarea */}
                <textarea
                    className="flex-1 block w-full max-h-[140px] py-2 px-3  text-gray-800 rounded-3xl resize-none placeholder:text-gray-500 focus:outline-none"
                    ref={textareaRef}
                    rows="1"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask me anything..."
                />

                {/* Action buttons (right side) */}
                <div className="flex items-center space-x-2 pr-2">
                    <button
                        className="p-2 rounded-full hover:bg-gray-200 text-gray-600 disabled:opacity-50"
                        onClick={submitNewMessage}
                        disabled={isLoading}
                        title="Send message"
                    >
                        <Send size={20} />
                    </button>
                    <button
                        className="p-2 rounded-full hover:bg-gray-200 text-gray-600"
                        title="Voice input"
                    >
                        <Mic size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
}

export default ChatInput;
