import { useState } from "react";
import Chatbot from "./chat/Chatbot";

export default function SidebarBot({ onClose }) {
    const [isMaximized, setIsMaximized] = useState(false);

    return (
        <div
            className={`
                fixed bg-[#F1F4F9] shadow-2xl border border-gray-200 z-50 flex flex-col transition-all duration-300 rounded-2xl
                ${isMaximized 
                    ? "inset-0 m-auto w-3/4 h-5/6"   // Centered, larger modal
                    : "bottom-10 right-10 w-120 h-200" // Sidebar position
                }
            `}
        >
            <div className="flex items-center justify-between p-4">
                <h2 className="text-lg font-semibold">Assistant</h2>
                <div className="flex space-x-2">
                    <button
                        onClick={() => setIsMaximized(!isMaximized)}
                        className="p-2 rounded-full hover:bg-gray-100"
                        title={isMaximized ? "Restore" : "Maximize"}
                    >
                        {isMaximized ? "🗗" : "🗖"}
                    </button>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full hover:bg-gray-100"
                        title="Close"
                    >
                        ✕
                    </button>
                </div>
            </div>
            <div className="flex-1 flex pt-4 pr-6 pl-6 pb-2 overflow-hidden">
                <Chatbot />
            </div>
        </div>
    );
}