/**
 * ISO 27001 Readiness Self-Assessment Chatbot — Frontend Logic
 * Handles the chat UI, API communication, score display, and PDF download.
 */

(function () {
    "use strict";

    // ============================
    // State
    // ============================
    const STATE = {
        sessionId: null,
        companyName: "",
        totalQuestions: 30,
        currentIndex: 0,
        isComplete: false,
        isProcessing: false,
        priorityMatrixLoaded: false,
        user: null,
    };

    // ============================
    // Authentication Functions
    // ============================

    function showAuthForm(form) {
        if (form === "login") {
            authLoginTab.classList.add("active");
            authSignupTab.classList.remove("active");
            loginForm.classList.add("active");
            signupForm.classList.remove("active");
            loginError.style.display = "none";
            signupError.style.display = "none";
        } else {
            authLoginTab.classList.remove("active");
            authSignupTab.classList.add("active");
            loginForm.classList.remove("active");
            signupForm.classList.add("active");
            loginError.style.display = "none";
            signupError.style.display = "none";
        }
    }

    function checkAuth() {
        fetch("/api/me")
            .then((r) => r.json())
            .then((data) => {
                if (data.user) {
                    STATE.user = data.user;
                    onAuthSuccess(data.user);
                } else {
                    showAuthScreen();
                }
            })
            .catch(() => showAuthScreen());
    }

    function onAuthSuccess(user) {
        userEmailDisplay.textContent = user.email;
        userEmailDisplay.style.display = "inline";
        logoutBtn.style.display = "inline-flex";
        authScreen.classList.remove("active");
        startScreen.classList.add("active");
        // Pre-fill company name
        if (user.company_name) {
            companyInput.value = user.company_name;
        }
    }

    function showAuthScreen() {
        authScreen.classList.add("active");
        startScreen.classList.remove("active");
        chatScreen.classList.remove("active");
        resultsScreen.classList.remove("active");
        userEmailDisplay.style.display = "none";
        logoutBtn.style.display = "none";
    }

    function loginUser() {
        const email = loginEmail.value.trim();
        const password = loginPassword.value.trim();
        loginError.style.display = "none";

        if (!email || !password) {
            loginError.textContent = "Please enter email and password.";
            loginError.style.display = "block";
            return;
        }

        loginBtn.disabled = true;
        loginBtn.textContent = "Logging in...";

        fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        })
        .then((r) => r.json())
        .then((data) => {
            loginBtn.disabled = false;
            loginBtn.textContent = "Log In";

            if (data.error) {
                loginError.textContent = data.error;
                loginError.style.display = "block";
                return;
            }

            STATE.user = data.user;
            onAuthSuccess(data.user);
        })
        .catch(() => {
            loginBtn.disabled = false;
            loginBtn.textContent = "Log In";
            loginError.textContent = "Network error. Please try again.";
            loginError.style.display = "block";
        });
    }

    function registerUser() {
        const email = signupEmail.value.trim();
        const password = signupPassword.value.trim();
        const companyName = signupName.value.trim();
        signupError.style.display = "none";

        if (!email || !password) {
            signupError.textContent = "Email and password are required.";
            signupError.style.display = "block";
            return;
        }

        if (password.length < 6) {
            signupError.textContent = "Password must be at least 6 characters.";
            signupError.style.display = "block";
            return;
        }

        signupBtn.disabled = true;
        signupBtn.textContent = "Creating account...";

        fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, company_name: companyName }),
        })
        .then((r) => r.json())
        .then((data) => {
            signupBtn.disabled = false;
            signupBtn.textContent = "Create Account";

            if (data.error) {
                signupError.textContent = data.error;
                signupError.style.display = "block";
                return;
            }

            STATE.user = data.user;
            onAuthSuccess(data.user);
        })
        .catch(() => {
            signupBtn.disabled = false;
            signupBtn.textContent = "Create Account";
            signupError.textContent = "Network error. Please try again.";
            signupError.style.display = "block";
        });
    }

    function logoutUser() {
        fetch("/api/logout", { method: "POST" })
            .then(() => {
                STATE.user = null;
                resetState();
                resetPriorityMatrixUI();
                loginEmail.value = "";
                loginPassword.value = "";
                signupEmail.value = "";
                signupPassword.value = "";
                signupName.value = "";
                showAuthScreen();
            })
            .catch(() => {});
    }

    // ============================
    // DOM References
    // ============================
    const $ = (id) => document.getElementById(id);
    const authScreen = $("auth-screen");
    const startScreen = $("start-screen");
    const chatScreen = $("chat-screen");
    const resultsScreen = $("results-screen");
    const companyInput = $("company-input");
    const startBtn = $("start-btn");
    const chatMessages = $("chat-messages");
    const answerInput = $("answer-input");
    const sendBtn = $("send-btn");
    const progressBar = $("progress-bar");
    const progressText = $("progress-text");
    const domainLabel = $("domain-label");
    const hintText = $("hint-text");
    const domainCards = $("domain-cards");
    const overallScoreValue = $("overall-score-value");
    const overallStatusText = $("overall-status-text");
    const resultsCompany = $("results-company");
    const downloadPdfBtn = $("download-pdf-btn");
    const restartBtn = $("restart-btn");
    const priorityMatrixSection = $("priority-matrix-section");
    const viewPriorityBtn = $("view-priority-btn");
    const priorityLoading = $("priority-loading");
    const priorityGrid = $("priority-grid");
    // Auth elements
    const userEmailDisplay = $("user-email-display");
    const logoutBtn = $("logout-btn");
    const authLoginTab = $("auth-login-tab");
    const authSignupTab = $("auth-signup-tab");
    const loginForm = $("login-form");
    const signupForm = $("signup-form");
    const loginEmail = $("login-email");
    const loginPassword = $("login-password");
    const loginBtn = $("login-btn");
    const loginError = $("login-error");
    const signupName = $("signup-name");
    const signupEmail = $("signup-email");
    const signupPassword = $("signup-password");
    const signupBtn = $("signup-btn");
    const signupError = $("signup-error");

    // ============================
    // Event Listeners
    // ============================

    // Auth - Tab switching
    authLoginTab.addEventListener("click", () => showAuthForm("login"));
    authSignupTab.addEventListener("click", () => showAuthForm("signup"));
    document.getElementById("login-to-signup").addEventListener("click", (e) => { e.preventDefault(); showAuthForm("signup"); });
    document.getElementById("signup-to-login").addEventListener("click", (e) => { e.preventDefault(); showAuthForm("login"); });

    // Auth - Login
    loginBtn.addEventListener("click", loginUser);
    loginPassword.addEventListener("keydown", (e) => { if (e.key === "Enter") loginUser(); });

    // Auth - Signup
    signupBtn.addEventListener("click", registerUser);
    signupPassword.addEventListener("keydown", (e) => { if (e.key === "Enter") registerUser(); });

    // Auth - Logout
    logoutBtn.addEventListener("click", logoutUser);

    // Start button
    startBtn.addEventListener("click", startAssessment);
    companyInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") startAssessment();
    });

    // Send button
    sendBtn.addEventListener("click", sendAnswer);
    answerInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendAnswer();
        }
    });

    // Input validation
    answerInput.addEventListener("input", toggleSendButton);

    // Restart
    restartBtn.addEventListener("click", restartAssessment);

    // Download PDF
    downloadPdfBtn.addEventListener("click", downloadPdf);

    // View Priority Matrix
    viewPriorityBtn.addEventListener("click", loadPriorityMatrix);

    // Home button
    const homeBtn = $("home-btn");
    homeBtn.addEventListener("click", goHome);

    // ============================
    // Initialization
    // ============================
    // Check if user is already logged in
    checkAuth();

    // ============================
    // Functions
    // ============================

    function startAssessment() {
        const name = companyInput.value.trim();
        if (!name) {
            companyInput.focus();
            companyInput.style.borderColor = "#f44336";
            setTimeout(() => { companyInput.style.borderColor = ""; }, 2000);
            return;
        }

        STATE.companyName = name;
        startBtn.disabled = true;
        startBtn.textContent = "Starting...";

        fetch("/api/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ company_name: name }),
        })
        .then((res) => res.json())
        .then((data) => {
            STATE.sessionId = data.session_id;
            STATE.totalQuestions = data.total_questions || 30;
            STATE.currentIndex = data.question_index;

            switchToChat();
            addBotMessage(data.question.text, data.question.hint);

            updateProgress(data.question_index, data.total_questions, data.question.domain);
            hintText.textContent = data.question.hint || "";

            answerInput.focus();
            startBtn.disabled = false;
            startBtn.textContent = "Start Assessment";
        })
        .catch((err) => {
            console.error("Start error:", err);
            startBtn.disabled = false;
            startBtn.textContent = "Start Assessment";
            addBotMessage("Sorry, there was an error starting the assessment. Please try again.");
        });
    }

    function sendAnswer() {
        const answer = answerInput.value.trim();
        if (!answer || STATE.isProcessing || STATE.isComplete) return;

        STATE.isProcessing = true;
        sendBtn.disabled = true;

        // Show user message
        addUserMessage(answer);
        answerInput.value = "";
        toggleSendButton();

        // Show typing indicator
        const typingId = showTypingIndicator();

        fetch("/api/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: STATE.sessionId,
                answer: answer,
            }),
        })
        .then((res) => res.json())
        .then((data) => {
            removeTypingIndicator(typingId);

            if (data.status === "next") {
                STATE.currentIndex = data.question_index;
                updateProgress(
                    data.question_index,
                    STATE.totalQuestions,
                    data.question.domain
                );

                // Show matched controls in a subtle way
                if (data.matched_controls && data.matched_controls.length > 0) {
                    addSystemMessage(
                        "Matched controls: " + data.matched_controls.join(", ")
                    );
                }

                addBotMessage(data.question.text, data.question.hint);
                hintText.textContent = data.question.hint || "";
                answerInput.focus();
            } else if (data.status === "done") {
                STATE.isComplete = true;
                hintText.textContent = "";

                // Show matched controls for last answer
                if (data.matched_controls && data.matched_controls.length > 0) {
                    addSystemMessage(
                        "Matched controls: " + data.matched_controls.join(", ")
                    );
                }

                // Brief delay then show results
                setTimeout(() => {
                    switchToResults(data);
                }, 800);
            }

            STATE.isProcessing = false;
            sendBtn.disabled = false;
            toggleSendButton();
        })
        .catch((err) => {
            console.error("Answer error:", err);
            removeTypingIndicator(typingId);
            addBotMessage("Sorry, there was an error processing your answer. Please try again.");
            STATE.isProcessing = false;
            sendBtn.disabled = false;
            toggleSendButton();
        });
    }

    function switchToChat() {
        startScreen.classList.remove("active");
        resultsScreen.classList.remove("active");
        chatScreen.classList.add("active");
        chatMessages.innerHTML = "";
    }

    function switchToResults(data) {
        chatScreen.classList.remove("active");
        resultsScreen.classList.add("active");

        resultsCompany.textContent = "Company: " + STATE.companyName;

        // Overall score
        const overall = data.overall_score || 0;
        overallScoreValue.textContent = overall;

        let statusText = "";
        let statusColor = "";
        if (overall >= 70) {
            statusText = "Good — Your organization shows strong ISO 27001 readiness.";
            statusColor = "#00c853";
        } else if (overall >= 40) {
            statusText = "Moderate — Several gaps identified. Priority improvements recommended.";
            statusColor = "#ff9800";
        } else {
            statusText = "Needs Improvement — Significant gaps exist across multiple domains.";
            statusColor = "#f44336";
        }
        overallStatusText.textContent = statusText;
        overallStatusText.style.color = statusColor;

        // Domain cards
        renderDomainCards(data.domain_scores);

        // Store report URL for download
        if (data.report_url) {
            downloadPdfBtn.dataset.url = data.report_url;
        } else {
            // Fetch report URL
            fetch(`/api/report/${STATE.sessionId}`)
                .then((r) => r.json())
                .then((rd) => {
                    downloadPdfBtn.dataset.url = rd.report_url;
                })
                .catch(() => {});
        }
    }

    function renderDomainCards(scores) {
        domainCards.innerHTML = "";
        const domainOrder = [
            "Organizational Controls",
            "People Controls",
            "Physical Controls",
            "Technological Controls",
            "Asset Management",
            "Cryptography",
            "Incident Management",
        ];

        domainOrder.forEach((domain) => {
            const score = scores[domain] || 0;
            const card = document.createElement("div");
            card.className = "domain-card";

            let scoreClass = "score-red";
            if (score >= 70) scoreClass = "score-green";
            else if (score >= 40) scoreClass = "score-yellow";

            // Shorten domain names for display
            let shortName = domain;
            if (domain === "Organizational Controls") shortName = "Organizational";
            else if (domain === "Technological Controls") shortName = "Technological";
            else if (domain === "Incident Management") shortName = "Incident Mgmt";
            else if (domain === "Asset Management") shortName = "Asset Mgmt";

            card.innerHTML = `
                <div class="domain-card-info">
                    <div class="domain-card-name">${shortName}</div>
                </div>
                <div class="domain-card-score ${scoreClass}">${score}%</div>
            `;
            domainCards.appendChild(card);
        });

        // Show the Priority Matrix section after domain cards
        priorityMatrixSection.style.display = "block";
    }

    // ============================
    // Priority Matrix
    // ============================

    function loadPriorityMatrix() {
        if (!STATE.sessionId) return;

        viewPriorityBtn.style.display = "none";
        priorityLoading.style.display = "flex";
        priorityGrid.style.display = "none";

        fetch(`/api/priority/${STATE.sessionId}`, {
            method: "POST",
        })
        .then((res) => res.json())
        .then((data) => {
            priorityLoading.style.display = "none";

            if (data.error) {
                // Show error message inline
                const errorDiv = document.createElement("div");
                errorDiv.className = "priority-error";
                if (data.error.includes("quota") || data.error.includes("429")) {
                    errorDiv.textContent = "⚠️ Priority Matrix is temporarily unavailable due to API rate limits. Please try again in a minute.";
                } else if (data.error.includes("not found") || data.error.includes("model")) {
                    errorDiv.textContent = "⚠️ Priority Matrix temporarily unavailable. Please try again later.";
                } else {
                    errorDiv.textContent = "⚠️ Could not generate Priority Matrix. " + data.error;
                }
                priorityLoading.parentNode.insertBefore(errorDiv, priorityLoading.nextSibling);
                viewPriorityBtn.style.display = "inline-flex";
                return;
            }

            renderPriorityGrid(data);
            priorityGrid.style.display = "grid";

            // Invalidate cached PDF URL so download regenerates with matrix
            downloadPdfBtn.dataset.url = "";
            STATE.priorityMatrixLoaded = true;
        })
        .catch((err) => {
            console.error("Priority matrix error:", err);
            priorityLoading.style.display = "none";
            const errorDiv = document.createElement("div");
            errorDiv.className = "priority-error";
            errorDiv.textContent = "⚠️ Network error. Please try again.";
            priorityLoading.parentNode.insertBefore(errorDiv, priorityLoading.nextSibling);
            viewPriorityBtn.style.display = "inline-flex";
        });
    }

    function renderPriorityGrid(data) {
        const quadrants = [
            { key: "fix_now", listId: "cell-fix-now-list" },
            { key: "plan_for_it", listId: "cell-plan-for-it-list" },
            { key: "quick_wins", listId: "cell-quick-wins-list" },
            { key: "deprioritize", listId: "cell-deprioritize-list" },
        ];

        quadrants.forEach(({ key, listId }) => {
            const listEl = document.getElementById(listId);
            if (!listEl) return;

            const items = data[key] || [];
            listEl.innerHTML = "";

            if (items.length === 0) {
                const emptyMsg = document.createElement("div");
                emptyMsg.className = "cell-empty";
                emptyMsg.textContent = "None — good job!";
                listEl.appendChild(emptyMsg);
                return;
            }

            items.forEach((item) => {
                const pill = document.createElement("span");
                pill.className = "control-pill";
                pill.textContent = `${item.id} · ${item.label}`;
                listEl.appendChild(pill);
            });
        });
    }

    function updateProgress(index, total, domain) {
        const pct = ((index + 1) / total) * 100;
        progressBar.style.width = Math.min(pct, 100) + "%";
        progressText.textContent = `Question ${index + 1} of ${total}`;
        if (domain) {
            domainLabel.textContent = "Domain: " + domain;
        }
    }

    function addBotMessage(text, hint) {
        const div = document.createElement("div");
        div.className = "message bot";
        div.innerHTML = `
            <div class="message-bubble">${escapeHtml(text)}</div>
            ${hint ? `<div class="message-meta">💡 ${escapeHtml(hint)}</div>` : ""}
        `;
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function addUserMessage(text) {
        const div = document.createElement("div");
        div.className = "message user";
        div.innerHTML = `
            <div class="message-bubble">${escapeHtml(text)}</div>
            <div class="message-meta">You</div>
        `;
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function addSystemMessage(text) {
        const div = document.createElement("div");
        div.className = "message bot";
        div.innerHTML = `
            <div class="message-bubble" style="background:#e8eaf6;font-size:12px;padding:8px 14px;">
                ${escapeHtml(text)}
            </div>
        `;
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const id = "typing-" + Date.now();
        const div = document.createElement("div");
        div.className = "message bot";
        div.id = id;
        div.innerHTML = `
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(div);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function toggleSendButton() {
        const text = answerInput.value.trim();
        sendBtn.disabled = !text || STATE.isProcessing || STATE.isComplete;
    }

    function downloadPdf() {
        const url = downloadPdfBtn.dataset.url;
        // If priority matrix was loaded, always regenerate to include it
        if (url && !STATE.priorityMatrixLoaded) {
            window.open(url, "_blank");
        } else {
            // Try fetching the report URL (triggers PDF regeneration)
            fetch(`/api/report/${STATE.sessionId}`)
                .then((r) => r.json())
                .then((data) => {
                    if (data.report_url) {
                        downloadPdfBtn.dataset.url = data.report_url;
                        window.open(data.report_url, "_blank");
                    }
                })
                .catch(() => {
                    alert("PDF report is not yet available. Please complete the assessment first.");
                });
        }
    }

    function restartAssessment() {
        resetState();
        resetPriorityMatrixUI();
        resultsScreen.classList.remove("active");
        chatScreen.classList.remove("active");
        startScreen.classList.add("active");
        companyInput.focus();
    }

    function goHome() {
        if (STATE.sessionId && !STATE.isComplete) {
            if (!confirm("Go back to home? Your current progress will be lost.")) return;
        }
        resetState();
        resetPriorityMatrixUI();
        resultsScreen.classList.remove("active");
        chatScreen.classList.remove("active");
        if (STATE.user) {
            startScreen.classList.add("active");
            companyInput.value = STATE.user.company_name || "";
            companyInput.focus();
        } else {
            showAuthScreen();
        }
        answerInput.value = "";
        chatMessages.innerHTML = "";
        downloadPdfBtn.dataset.url = "";
    }

    function resetState() {
        STATE.sessionId = null;
        STATE.companyName = "";
        STATE.currentIndex = 0;
        STATE.isComplete = false;
        STATE.isProcessing = false;
        STATE.priorityMatrixLoaded = false;
    }

    function resetPriorityMatrixUI() {
        priorityMatrixSection.style.display = "none";
        viewPriorityBtn.style.display = "inline-flex";
        priorityLoading.style.display = "none";
        priorityGrid.style.display = "none";
        // Clear all quadrant lists
        ["cell-fix-now-list", "cell-plan-for-it-list", "cell-quick-wins-list", "cell-deprioritize-list"].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = "";
        });
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
})();
