
export default function FloatingButton({ onClick }) {
    return (
        <div className="fixed bottom-6 right-6 z-50">
        <button
            onClick={onClick}
            className="w-16 h-16 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-lg"
            title="Ask Assistant all the doubts you have"
        >
            ASSISTANT
        </button>
        </div>
    );
}