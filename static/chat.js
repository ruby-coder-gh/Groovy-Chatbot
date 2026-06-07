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
        remediationPlans: [],
        remediationTemplates: [],
        remediationLoaded: false,
        remediationLoadingIndex: 0,
        remediationLoadingTimer: null,
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
    // Remediation elements
    const remediationSection = $("remediation-section");
    const generateRemediationBtn = $("generate-remediation-btn");
    const remediationLoading = $("remediation-loading");
    const remediationLoadingMsg = $("remediation-loading-message");
    const remediationError = $("remediation-error");
    const remediationSummary = $("remediation-summary");
    const summaryControls = $("summary-controls");
    const summaryHours = $("summary-hours");
    const summaryDomains = $("summary-domains");
    const remediationSortBar = $("remediation-sort-bar");
    const remediationAccordion = $("remediation-accordion");
    const remediationExportBar = $("remediation-export-bar");
    const exportCsvBtn = $("export-csv-btn");
    const policyTemplatesSection = $("policy-templates-section");
    const policyTemplatesList = $("policy-templates-list");
    const expandAllBtn = $("expand-all-btn");
    const collapseAllBtn = $("collapse-all-btn");
    const dashboardPill = $("dashboard-pill");
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

    // Generate Remediation Plan
    generateRemediationBtn.addEventListener("click", generateRemediationPlan);

    // Export CSV
    exportCsvBtn.addEventListener("click", exportRemediationCsv);

    // Expand / Collapse All
    expandAllBtn.addEventListener("click", () => toggleAllAccordionItems(true));
    collapseAllBtn.addEventListener("click", () => toggleAllAccordionItems(false));

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

            if (data.dashboard_url) {
                dashboardPill.href = data.dashboard_url;
                dashboardPill.style.display = "flex";
            }

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

                addBotMessage(data.question.text, data.question.hint);
                hintText.textContent = data.question.hint || "";
                answerInput.focus();
            } else if (data.status === "done") {
                STATE.isComplete = true;
                hintText.textContent = "";

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

        // Animate conic gradient percentage on the score ring
        const scoreRing = document.querySelector(".overall-score-ring");
        if (scoreRing) {
            scoreRing.style.setProperty("--pct", overall + "%");
        }

        let statusText = "";
        let statusColor = "";
        if (overall >= 70) {
            statusText = "Good — Your organization shows strong ISO 27001 readiness.";
            statusColor = "#10b981";
        } else if (overall >= 40) {
            statusText = "Moderate — Several gaps identified. Priority improvements recommended.";
            statusColor = "#f59e0b";
        } else {
            statusText = "Needs Improvement — Significant gaps exist across multiple domains.";
            statusColor = "#ef4444";
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

        // Show the Priority Matrix and Remediation sections after domain cards
        priorityMatrixSection.style.display = "block";
        remediationSection.style.display = "block";
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

    // ============================
    // Remediation Plan
    // ============================

    const REMEDIATION_MESSAGES = [
        "Consulting AI for remediation strategies...",
        "Analyzing gap control requirements...",
        "Estimating effort hours for each control...",
        "Assigning ownership roles...",
        "Generating policy template clauses...",
        "Finalizing remediation roadmap...",
    ];

    function generateRemediationPlan() {
        if (!STATE.sessionId) return;

        generateRemediationBtn.style.display = "none";
        remediationLoading.style.display = "flex";
        remediationError.style.display = "none";
        remediationAccordion.style.display = "none";
        remediationSummary.style.display = "none";
        remediationSortBar.style.display = "none";
        remediationExportBar.style.display = "none";
        policyTemplatesSection.style.display = "none";

        // Start cycling loading messages
        STATE.remediationLoadingIndex = 0;
        remediationLoadingMsg.textContent = REMEDIATION_MESSAGES[0];
        STATE.remediationLoadingTimer = setInterval(() => {
            STATE.remediationLoadingIndex = (STATE.remediationLoadingIndex + 1) % REMEDIATION_MESSAGES.length;
            remediationLoadingMsg.textContent = REMEDIATION_MESSAGES[STATE.remediationLoadingIndex];
        }, 2500);

        fetch(`/api/remediation/${STATE.sessionId}`, {
            method: "POST",
        })
        .then((res) => {
            // Handle non-JSON or error responses gracefully
            const contentType = res.headers.get("content-type") || "";
            if (!contentType.includes("application/json")) {
                if (res.status === 429 || res.status === 500) {
                    throw new Error("RATE_LIMIT");
                }
                throw new Error("INVALID_RESPONSE");
            }
            return res.json();
        })
        .then((data) => {
            clearInterval(STATE.remediationLoadingTimer);
            remediationLoading.style.display = "none";

            if (data.error) {
                // Show friendly message for quota errors
                const isQuota = data.error.includes("429") || data.error.includes("quota") || data.error.includes("rate limit");
                if (isQuota) {
                    // Extract retry delay from Gemini's "Please retry in Xs" message
                    const retryMatch = data.error.match(/retry\s+in\s+(\d+(?:\.\d+)?)s/i);
                    let retrySeconds = 60;
                    if (retryMatch && retryMatch[1]) {
                        retrySeconds = Math.ceil(parseFloat(retryMatch[1]));
                    }
                    remediationError.innerHTML = `
                        &#x26A0;&#xFE0F; <strong>AI service temporarily unavailable</strong><br>
                        The Gemini API free-tier quota has been reached.<br>
                        Please wait <span id="retry-countdown">${retrySeconds}</span> seconds, then try again.
                        <br><br>
                        <button id="retry-remediation-btn" class="btn btn-sm" style="background:var(--primary);color:#fff;border:none;padding:8px 20px;border-radius:20px;cursor:pointer;">
                            &#x1F504; Retry Now
                        </button>
                    `;
                    // Countdown timer
                    let seconds = retrySeconds;
                    const countdownEl = document.getElementById("retry-countdown");
                    const countdownTimer = setInterval(() => {
                        seconds--;
                        if (countdownEl) countdownEl.textContent = Math.max(0, seconds);
                        if (seconds <= 0) {
                            clearInterval(countdownTimer);
                            if (countdownEl) countdownEl.textContent = "0";
                        }
                    }, 1000);
                    // Retry button
                    setTimeout(() => {
                        const retryBtn = document.getElementById("retry-remediation-btn");
                        if (retryBtn) {
                            retryBtn.addEventListener("click", () => {
                                clearInterval(countdownTimer);
                                generateRemediationPlan();
                            });
                        }
                    }, 0);
                } else {
                    remediationError.textContent = "⚠️ " + data.error;
                }
                remediationError.style.display = "block";
                generateRemediationBtn.style.display = "inline-flex";
                return;
            }

            STATE.remediationPlans = data.plans || [];
            STATE.remediationTemplates = data.policy_templates || [];
            STATE.remediationLoaded = true;

            // Invalidate cached PDF URL so download regenerates with remediation data
            downloadPdfBtn.dataset.url = "";

            renderRemediationPlan(data.plans, data.policy_templates);
        })
        .catch((err) => {
            console.error("Remediation error:", err);
            clearInterval(STATE.remediationLoadingTimer);
            remediationLoading.style.display = "none";
            const isQuota = err.message === "RATE_LIMIT";
            if (isQuota) {
                remediationError.innerHTML = `
                    &#x26A0;&#xFE0F; <strong>AI service temporarily unavailable</strong><br>
                    The Gemini API free-tier quota has been reached. Please wait a moment and try again.
                    <br><br>
                    <button id="retry-remediation-btn" class="btn btn-sm" style="background:var(--primary);color:#fff;border:none;padding:8px 20px;border-radius:20px;cursor:pointer;">
                        &#x1F504; Retry Now
                    </button>
                `;
                setTimeout(() => {
                    const retryBtn = document.getElementById("retry-remediation-btn");
                    if (retryBtn) {
                        retryBtn.addEventListener("click", generateRemediationPlan);
                    }
                }, 0);
            } else {
                remediationError.innerHTML = `
                    &#x1F6AB; <strong>Network error</strong><br>
                    Could not connect to the server. Please check your connection and try again.
                `;
            }
            remediationError.style.display = "block";
            generateRemediationBtn.style.display = "inline-flex";
        });
    }

    function renderRemediationPlan(plans, templates) {
        if (!plans || plans.length === 0) {
            remediationAccordion.innerHTML = `
                <div class="remediation-empty">
                    &#x2705; No gaps found — all controls are adequately addressed!
                </div>
            `;
            remediationAccordion.style.display = "block";
            return;
        }

        // Summary bar
        const totalHours = plans.reduce((sum, p) => sum + (p.effort_hours || 0), 0);
        const uniqueDomains = [...new Set(plans.map((p) => p.domain))];
        summaryControls.textContent = plans.length;
        summaryHours.textContent = totalHours;
        summaryDomains.textContent = uniqueDomains.length;
        remediationSummary.style.display = "flex";
        remediationSortBar.style.display = "flex";
        remediationExportBar.style.display = "flex";

        // Render accordion with default sort (domain)
        renderAccordion(plans);
        remediationAccordion.style.display = "block";

        // Set sort button handlers
        document.querySelectorAll(".sort-btn[data-sort]").forEach((btn) => {
            btn.addEventListener("click", function () {
                document.querySelectorAll(".sort-btn[data-sort]").forEach((b) => b.classList.remove("active"));
                this.classList.add("active");
                const sortBy = this.dataset.sort;
                const sorted = sortPlans(plans, sortBy);
                renderAccordion(sorted);
            });
        });

        // Policy templates
        if (templates && templates.length > 0) {
            renderPolicyTemplates(templates);
            policyTemplatesSection.style.display = "block";
        }
    }

    function renderAccordion(plans) {
        const container = remediationAccordion;
        container.innerHTML = "";

        plans.forEach((plan, index) => {
            const item = document.createElement("div");
            item.className = "accordion-item";

            // Effort badge color
            const hours = plan.effort_hours || 0;
            let badgeClass = "badge-effort-low";
            if (hours > 30) badgeClass = "badge-effort-high";
            else if (hours > 7) badgeClass = "badge-effort-medium";

            item.innerHTML = `
                <div class="accordion-header" data-index="${index}">
                    <span class="accordion-toggle">&#x25B6;</span>
                    <span class="accordion-control-id">${escapeHtml(plan.control_id)}</span>
                    <span class="accordion-domain">${escapeHtml(plan.domain)}</span>
                    <span class="accordion-owner">${escapeHtml(plan.owner)}</span>
                    <span class="effort-badge ${badgeClass}">${hours}h</span>
                </div>
                <div class="accordion-body">
                    <div class="accordion-description">${escapeHtml(plan.description)}</div>
                    <div class="accordion-meta">
                        <span><strong>Owner:</strong> ${escapeHtml(plan.owner)}</span>
                        <span><strong>Effort:</strong> ${hours} hours</span>
                        <span><strong>Domain:</strong> ${escapeHtml(plan.domain)}</span>
                    </div>
                </div>
            `;

            // Toggle on header click
            item.querySelector(".accordion-header").addEventListener("click", () => {
                const body = item.querySelector(".accordion-body");
                const toggle = item.querySelector(".accordion-toggle");
                const isOpen = body.classList.contains("open");
                body.classList.toggle("open");
                toggle.classList.toggle("open");
                toggle.innerHTML = isOpen ? "&#x25B6;" : "&#x25BC;";
            });

            container.appendChild(item);
        });
    }

    function sortPlans(plans, sortBy) {
        const sorted = [...plans];
        switch (sortBy) {
            case "domain":
                sorted.sort((a, b) => a.domain.localeCompare(b.domain) || a.control_id.localeCompare(b.control_id));
                break;
            case "effort":
                sorted.sort((a, b) => (a.effort_hours || 0) - (b.effort_hours || 0));
                break;
            case "owner":
                sorted.sort((a, b) => a.owner.localeCompare(b.owner) || a.control_id.localeCompare(b.control_id));
                break;
        }
        return sorted;
    }

    function toggleAllAccordionItems(expand) {
        document.querySelectorAll(".accordion-body").forEach((body) => {
            body.classList.toggle("open", expand);
        });
        document.querySelectorAll(".accordion-toggle").forEach((toggle) => {
            toggle.classList.toggle("open", expand);
            toggle.innerHTML = expand ? "&#x25BC;" : "&#x25B6;";
        });
    }

    function renderPolicyTemplates(templates) {
        policyTemplatesList.innerHTML = "";

        templates.forEach((tmpl) => {
            const block = document.createElement("div");
            block.className = "policy-block";

            block.innerHTML = `
                <div class="policy-block-header">
                    <strong>${escapeHtml(tmpl.title)}</strong>
                    <span class="policy-control-id">${escapeHtml(tmpl.control_id)}</span>
                </div>
                <blockquote class="policy-clause">${escapeHtml(tmpl.clause)}</blockquote>
                <button class="btn btn-sm copy-template-btn" data-clause="${escapeHtml(tmpl.clause)}">
                    &#x1F4CB; Copy template
                </button>
                <span class="copy-feedback" style="display:none;">Copied &#x2714;</span>
            `;

            block.querySelector(".copy-template-btn").addEventListener("click", function () {
                const clause = this.dataset.clause;
                navigator.clipboard.writeText(clause).then(() => {
                    const feedback = this.nextElementSibling;
                    feedback.style.display = "inline";
                    setTimeout(() => {
                        feedback.style.display = "none";
                    }, 2000);
                }).catch(() => {
                    // Fallback
                    const textarea = document.createElement("textarea");
                    textarea.value = clause;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand("copy");
                    document.body.removeChild(textarea);
                    const feedback = this.nextElementSibling;
                    feedback.style.display = "inline";
                    setTimeout(() => {
                        feedback.style.display = "none";
                    }, 2000);
                });
            });

            policyTemplatesList.appendChild(block);
        });
    }

    function exportRemediationCsv() {
        const plans = STATE.remediationPlans;
        if (!plans || plans.length === 0) return;

        // BOM for Excel UTF-8
        const BOM = "\uFEFF";
        const headers = ["Control ID", "Domain", "Description", "Effort Hours", "Owner"];
        const rows = plans.map((p) => [
            p.control_id,
            p.domain,
            `"${(p.description || "").replace(/"/g, '""')}"`,
            p.effort_hours || 0,
            p.owner,
        ]);

        const csv = BOM + headers.join(",") + "\n" + rows.map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `remediation_plan_${STATE.sessionId || "export"}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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
        STATE.remediationPlans = [];
        STATE.remediationTemplates = [];
        STATE.remediationLoaded = false;
        if (STATE.remediationLoadingTimer) {
            clearInterval(STATE.remediationLoadingTimer);
            STATE.remediationLoadingTimer = null;
        }
        if (dashboardPill) {
            dashboardPill.style.display = "none";
            dashboardPill.href = "#";
        }
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
        // Reset remediation UI
        remediationSection.style.display = "none";
        generateRemediationBtn.style.display = "inline-flex";
        remediationLoading.style.display = "none";
        remediationError.style.display = "none";
        remediationAccordion.style.display = "none";
        remediationAccordion.innerHTML = "";
        remediationSummary.style.display = "none";
        remediationSortBar.style.display = "none";
        remediationExportBar.style.display = "none";
        policyTemplatesSection.style.display = "none";
        policyTemplatesList.innerHTML = "";
        if (STATE.remediationLoadingTimer) {
            clearInterval(STATE.remediationLoadingTimer);
            STATE.remediationLoadingTimer = null;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
})();
