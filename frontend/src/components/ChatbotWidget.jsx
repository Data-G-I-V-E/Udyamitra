import FloatingButton from "./FloatingButton";
import SidebarBot from "./SidebarBot";
import { useState } from "react";

export default function ChatbotWidget() {
    const [isOpen, setIsOpen] = useState(false);
    return (
        <>
        {!isOpen && <FloatingButton onClick={() => setIsOpen(true)} />}
        {isOpen && <SidebarBot onClose={() => setIsOpen(false)} />}
        </>
    );
}