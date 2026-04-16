import { useState, useRef, useEffect } from "react";
import { useIsMobile } from "../hooks/useIsMobile";

export default function ChatInput({ onSend, isStreaming = false }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);
  const isMobile = useIsMobile();

  // Auto-resize textarea as user types
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [text]);

  const handleSend = () => {
    if (!text.trim() || isStreaming) return;
    onSend(text);
    setText("");
    // Reset height
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e) => {
    // On desktop: Enter sends, Shift+Enter adds newline
    // On mobile: never intercept Enter (user should use the send button)
    if (!isMobile && e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const charCount = text.length;
  const atLimit = charCount >= 4000;
  const btnSize = isMobile ? "40px" : "32px";

  return (
    <div
      style={{
        padding: isMobile ? "12px 12px" : "16px 20px",
        borderTop: "1px solid #1e2130",
        background: "#0f1117",
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: "10px",
          background: "#161a24",
          border: "1px solid #1e2130",
          borderRadius: "12px",
          padding: isMobile ? "10px 12px" : "10px 14px",
          transition: "border-color 0.15s ease",
        }}
        onFocusCapture={(e) => {
          e.currentTarget.style.borderColor = "rgba(200,241,53,0.3)";
        }}
        onBlurCapture={(e) => {
          e.currentTarget.style.borderColor = "#1e2130";
        }}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 4000))}
          onKeyDown={handleKeyDown}
          placeholder="Ask your coach anything…"
          rows={1}
          disabled={isStreaming}
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            resize: "none",
            fontSize: isMobile ? "16px" : "13px",  // 16px prevents iOS zoom on focus
            color: "#f0f4f8",
            lineHeight: "1.6",
            fontFamily: "inherit",
            overflowY: "auto",
            maxHeight: "160px",
          }}
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!text.trim() || isStreaming}
          style={{
            flexShrink: 0,
            width: btnSize,
            height: btnSize,
            borderRadius: "8px",
            border: "none",
            background:
              text.trim() && !isStreaming
                ? "#c8f135"
                : "rgba(200,241,53,0.08)",
            color:
              text.trim() && !isStreaming ? "#0f1117" : "#4a5568",
            cursor:
              text.trim() && !isStreaming ? "pointer" : "not-allowed",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.15s ease",
            fontSize: isMobile ? "18px" : "16px",
            fontWeight: "700",
            WebkitTapHighlightColor: "transparent",
          }}
          aria-label="Send message"
        >
          {isStreaming ? (
            <span style={{ fontSize: "10px", letterSpacing: "2px" }}>···</span>
          ) : (
            "↑"
          )}
        </button>
      </div>

      {/* Footer row — hint (desktop only) + char count */}
      <div
        style={{
          display: "flex",
          justifyContent: isMobile ? "flex-end" : "space-between",
          alignItems: "center",
          paddingLeft: "2px",
          paddingRight: "2px",
        }}
      >
        {!isMobile && (
          <span style={{ fontSize: "10px", color: "#2d3748" }}>
            Enter to send · Shift+Enter for new line
          </span>
        )}
        <span
          style={{
            fontSize: "10px",
            color: atLimit ? "#e53e3e" : "#2d3748",
          }}
        >
          {charCount}/4000
        </span>
      </div>
    </div>
  );
}
