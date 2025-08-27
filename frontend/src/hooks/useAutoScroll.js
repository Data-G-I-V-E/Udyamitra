import { useEffect, useLayoutEffect, useRef } from "react";

const SCROLL_THRESHOLD = 10;

function useAutoScroll(active) {
    const scrollContentRef = useRef(null);
    const isDisabled = useRef(false);
    const prevScrollTop = useRef(null);

    useEffect(() => {
        const el = scrollContentRef.current;
        if (!el) return;

        const resizeObserver = new ResizeObserver(() => {
        const { scrollHeight, clientHeight, scrollTop } = el;
        if (!isDisabled.current && scrollHeight - clientHeight > scrollTop) {
            el.scrollTo({
            top: scrollHeight - clientHeight,
            behavior: "smooth",
            });
        }
        });

        resizeObserver.observe(el);
        return () => resizeObserver.disconnect();
    }, []);

    useLayoutEffect(() => {
        const el = scrollContentRef.current;
        if (!el) return;

        if (!active) {
        isDisabled.current = true;
        return;
        }

        function onScroll() {
        const { scrollHeight, clientHeight, scrollTop } = el;

        if (
            !isDisabled.current &&
            scrollTop < prevScrollTop.current &&
            scrollHeight - clientHeight > scrollTop + SCROLL_THRESHOLD
        ) {
            isDisabled.current = true;
        } else if (
            isDisabled.current &&
            scrollHeight - clientHeight <= scrollTop + SCROLL_THRESHOLD
        ) {
            isDisabled.current = false;
        }
        prevScrollTop.current = scrollTop;
        }

        isDisabled.current = false;
        prevScrollTop.current = el.scrollTop;
        el.addEventListener("scroll", onScroll);

        return () => el.removeEventListener("scroll", onScroll);
    }, [active]);

    return scrollContentRef;
}

export default useAutoScroll;