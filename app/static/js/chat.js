// Decision Maker AI Chat Widget
document.addEventListener("DOMContentLoaded", () => {
    const launcherBtn = document.getElementById("chatLauncherBtn");
    const chatPanel = document.getElementById("chatPanel");
    const closeBtn = document.getElementById("chatCloseBtn");
    const clearBtn = document.getElementById("chatClearBtn");
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const typingIndicator = document.getElementById("typingIndicator");

    if (!launcherBtn || !chatPanel || !chatForm || !chatInput || !chatMessages) {
        return;
    }

    // Session ID management
    let sessionId = localStorage.getItem("dm_session_id");
    if (!sessionId) {
        sessionId = "sess_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
        localStorage.setItem("dm_session_id", sessionId);
    }

    // Open & Close handlers
    function toggleChat(show) {
        if (show === undefined) {
            chatPanel.classList.toggle("hidden");
        } else if (show) {
            chatPanel.classList.remove("hidden");
        } else {
            chatPanel.classList.add("hidden");
        }

        if (!chatPanel.classList.contains("hidden")) {
            setTimeout(() => chatInput.focus(), 150);
            scrollToBottom();
        }
    }

    launcherBtn.addEventListener("click", () => toggleChat());
    closeBtn.addEventListener("click", () => toggleChat(false));

    // Clear history handler
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (confirm("Reset chat messages for this session?")) {
                chatMessages.innerHTML = `
                    <div class="flex items-start space-x-2">
                        <div class="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs shrink-0 mt-0.5">
                            <i class="fa-solid fa-robot"></i>
                        </div>
                        <div class="bg-white p-3.5 rounded-2xl rounded-tl-sm shadow-sm border border-slate-100 max-w-[85%] text-slate-800">
                            <p class="text-xs font-semibold text-indigo-600 mb-1">Decision Assistant</p>
                            <p class="text-sm">Chat history cleared. How can I assist you with your decisions?</p>
                        </div>
                    </div>
                `;
            }
        });
    }

    // Global helper to open chat and prefill/send context
    window.openChatWithContext = function(promptText, autoSend = false) {
        toggleChat(true);
        chatInput.value = promptText;
        if (autoSend) {
            sendMessage(promptText);
        } else {
            chatInput.focus();
        }
    };

    // Quick Prompt Chips
    document.addEventListener("click", (e) => {
        if (e.target && e.target.classList.contains("chat-chip")) {
            const prompt = e.target.innerText.trim();
            chatInput.value = prompt;
            sendMessage(prompt);
        }
    });

    // Send Message Form Submit
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;
        sendMessage(text);
    });

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function formatMarkdown(text) {
        // Escape basic HTML
        let safe = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        // Bold: **text**
        safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        // Line breaks
        safe = safe.replace(/\n\n/g, "</p><p class='mt-2'>").replace(/\n/g, "<br>");
        return `<p>${safe}</p>`;
    }

    async function sendMessage(text) {
        chatInput.value = "";
        
        // Append user bubble
        appendUserMessage(text);
        scrollToBottom();

        // Show typing indicator
        typingIndicator.classList.remove("hidden");
        scrollToBottom();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId
                })
            });

            typingIndicator.classList.add("hidden");

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                appendBotMessage(
                    errData.description || "Sorry, I encountered an issue processing your request. Please try again shortly.",
                    "Error",
                    null
                );
                return;
            }

            const data = await response.json();
            appendBotMessage(data.reply, data.source, data.ticket_id);
        } catch (err) {
            typingIndicator.classList.add("hidden");
            appendBotMessage(
                "Network error: Unable to contact the assistant server. Please check your internet connection.",
                "NetworkError",
                null
            );
        } finally {
            scrollToBottom();
        }
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "flex items-start justify-end space-x-2";
        msgDiv.innerHTML = `
            <div class="bg-indigo-600 text-white p-3.5 rounded-2xl rounded-tr-sm shadow-sm max-w-[85%] text-sm">
                <p>${text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>
            </div>
            <div class="w-7 h-7 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center text-xs shrink-0 mt-0.5 font-bold">
                <i class="fa-solid fa-user"></i>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
    }

    function appendBotMessage(replyText, source, ticketId) {
        const messageId = "msg_" + Math.random().toString(36).substring(2, 9);
        const msgDiv = document.createElement("div");
        msgDiv.className = "flex items-start space-x-2";

        const badgeHtml = source ? `<span class="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded ml-2 font-mono">${source}</span>` : "";

        msgDiv.innerHTML = `
            <div class="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs shrink-0 mt-0.5">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="bg-white p-3.5 rounded-2xl rounded-tl-sm shadow-sm border border-slate-100 max-w-[85%] text-slate-800">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-semibold text-indigo-600">Decision Assistant</span>
                    ${badgeHtml}
                </div>
                <div class="chat-markdown text-sm text-slate-700 leading-relaxed">
                    ${formatMarkdown(replyText)}
                </div>
                
                <!-- Feedback Thumbs -->
                <div class="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                    <span class="text-[11px]">Was this helpful?</span>
                    <div class="flex items-center space-x-1" id="fb_${messageId}">
                        <button type="button" class="btn-fb-up p-1 rounded hover:bg-slate-100 hover:text-emerald-600 transition-colors" title="Helpful">
                            <i class="fa-regular fa-thumbs-up"></i>
                        </button>
                        <button type="button" class="btn-fb-down p-1 rounded hover:bg-slate-100 hover:text-rose-600 transition-colors" title="Not helpful">
                            <i class="fa-regular fa-thumbs-down"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        chatMessages.appendChild(msgDiv);

        // Feedback buttons listener
        const fbContainer = msgDiv.querySelector(`#fb_${messageId}`);
        if (fbContainer) {
            const upBtn = fbContainer.querySelector(".btn-fb-up");
            const downBtn = fbContainer.querySelector(".btn-fb-down");

            upBtn.addEventListener("click", () => sendFeedback(messageId, 1, fbContainer));
            downBtn.addEventListener("click", () => sendFeedback(messageId, -1, fbContainer));
        }
    }

    async function sendFeedback(messageId, rating, container) {
        container.innerHTML = `<span class="text-[11px] text-emerald-600 font-medium"><i class="fa-solid fa-check mr-1"></i>Feedback noted!</span>`;
        try {
            await fetch("/api/feedback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message_id: messageId,
                    rating: rating
                })
            });
        } catch (e) {
            // Fail silently
        }
    }
});
