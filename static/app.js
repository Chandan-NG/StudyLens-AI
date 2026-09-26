/**
 * StudyLens AI — Frontend Application Logic.
 * Fast, reactive single-page application communicating with the FastAPI backend.
 */

// Global State
const state = {
    activeNav: 'session',
    activeTab: 'transcript',
    transcriptMode: 'continuous',
    chatMode: 'Video + Web Research',
    video_id: null,
    video_url: null,
    clean_transcript: '',
    timestamped_transcript: '',
    stats: null,
    summary: null,
    notes: null,
    quiz: null,
    quizSubmitted: false,
    userAnswers: {},
    chatHistory: [],
    settings: {
        ollama_host: 'http://localhost:11434',
        ollama_model: 'qwen2:7b',
        web_research_enabled: true,
        available_models: []
    }
};

// --- Safe Network Fetch Helper ---
// Prevents "SyntaxError: Unexpected token 'I', 'Internal S'..." when server errors occur
async function safeFetchJson(url, options = {}) {
    try {
        const res = await fetch(url, options);
        const text = await res.text();
        try {
            return JSON.parse(text);
        } catch {
            return {
                success: false,
                error: `Server returned non-JSON response (${res.status}): ${text.substring(0, 180)}`
            };
        }
    } catch (err) {
        return {
            success: false,
            error: `Network connection error: ${err.message || err}`
        };
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    fetchSettings();
});

// --- Navigation Switching ---
function switchNav(nav) {
    state.activeNav = nav;
    document.querySelectorAll('.nav-pill-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(sec => sec.style.display = 'none');

    document.getElementById(`nav-btn-${nav}`).classList.add('active');
    document.getElementById(`view-${nav}`).style.display = 'block';

    if (nav === 'history') {
        loadHistory();
    } else if (nav === 'settings') {
        fetchSettings();
    }
}

// --- Tab Switching ---
function switchTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll('.tab-pill').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

    document.getElementById(`tab-btn-${tab}`).classList.add('active');
    document.getElementById(`tab-content-${tab}`).classList.add('active');
}

// --- Settings & Status ---
async function fetchSettings() {
    try {
        const data = await safeFetchJson('/api/settings');
        if (!data) return;
        state.settings = data;

        // Update sidebar status badge
        const dot = document.getElementById('sidebar-status-dot');
        const modelLabel = document.getElementById('sidebar-model-name');
        modelLabel.textContent = data.ollama_model || 'qwen2:7b';
        if (data.ollama_online) {
            dot.className = 'status-dot';
            dot.title = 'Ollama Online';
        } else {
            dot.className = 'status-dot offline';
            dot.title = 'Ollama Offline';
        }

        // Update settings form
        if (document.getElementById('settings-host')) {
            document.getElementById('settings-host').value = data.ollama_host || 'http://localhost:11434';
            document.getElementById('settings-web-default').checked = data.web_research_enabled !== false;

            const select = document.getElementById('settings-model-select');
            const input = document.getElementById('settings-model-input');
            if (data.available_models && data.available_models.length > 0) {
                select.innerHTML = '';
                data.available_models.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m;
                    opt.textContent = m;
                    if (m === data.ollama_model) opt.selected = true;
                    select.appendChild(opt);
                });
                select.style.display = 'block';
                input.style.display = 'none';
            } else {
                select.style.display = 'none';
                input.style.display = 'block';
                input.value = data.ollama_model || 'qwen2:7b';
            }
        }

        state.chatMode = data.web_research_enabled !== false ? 'Video + Web Research' : 'Video Only';
        updateChatModeUI();
    } catch (err) {
        console.warn('Failed to fetch settings:', err);
    }
}

async function saveSettings() {
    const host = document.getElementById('settings-host').value.trim();
    const select = document.getElementById('settings-model-select');
    const input = document.getElementById('settings-model-input');
    const model = (select.style.display !== 'none' ? select.value : input.value).trim();
    const webDefault = document.getElementById('settings-web-default').checked;

    const data = await safeFetchJson('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host, model, web_research_enabled: webDefault })
    });
    if (data.success) {
        alert('Settings saved successfully.');
        fetchSettings();
    } else {
        alert('Error saving settings: ' + (data.error || 'Unknown error'));
    }
}

// --- Load Video & Transcript ---
async function handleLoadVideo(e) {
    if (e && e.preventDefault) e.preventDefault();
    const urlInput = document.getElementById('video-url-input');
    const url = urlInput.value.trim();
    if (!url) return;

    const btn = document.getElementById('btn-load-video');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border-sm"></span> Loading...';
    btn.disabled = true;

    try {
        const data = await safeFetchJson('/api/video/load', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (data.success) {
            populateSession(data);
        } else {
            alert(data.error || 'Failed to load video transcript.');
        }
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function populateSession(data) {
    state.video_id = data.video_id;
    state.video_url = data.url;
    state.clean_transcript = data.clean_transcript;
    state.timestamped_transcript = data.timestamped_transcript;
    state.stats = data.stats;
    state.summary = data.summary || null;
    state.notes = data.notes || null;
    state.quiz = data.quiz || null;
    state.quizSubmitted = false;
    state.userAnswers = {};
    state.chatHistory = [];

    // Active lecture banner
    const banner = document.getElementById('lecture-banner');
    banner.style.display = 'flex';
    document.getElementById('lecture-stats-text').innerHTML = 
        `<i class="bi bi-journal-text" style="margin-right: 4px;"></i> ${data.stats.word_count.toLocaleString()} words &nbsp;·&nbsp; <i class="bi bi-clock-history" style="margin-right: 4px;"></i> ~${data.stats.reading_time_minutes} min read`;

    // Populate Tab 1: Transcript
    document.getElementById('transcript-empty-state').style.display = 'none';
    document.getElementById('transcript-content').style.display = 'grid';
    document.getElementById('youtube-player').src = `https://www.youtube-nocookie.com/embed/${data.video_id}`;
    document.getElementById('video-source-caption').textContent = `Source: ${data.url}`;
    renderTranscript();

    // Populate Tab 2: Summary
    if (state.summary) {
        showSummaryView(state.summary);
    } else {
        document.getElementById('summary-empty-state').style.display = 'block';
        document.getElementById('summary-content').style.display = 'none';
        document.getElementById('btn-gen-summary').style.display = 'inline-flex';
        document.getElementById('summary-empty-text').textContent = 'Extract key takeaways, core concepts, and main arguments from this video.';
    }

    // Populate Tab 3: Notes
    if (state.notes) {
        showNotesView(state.notes);
    } else {
        document.getElementById('notes-empty-state').style.display = 'block';
        document.getElementById('notes-content').style.display = 'none';
        document.getElementById('btn-gen-notes').style.display = 'inline-flex';
        document.getElementById('notes-empty-text').textContent = 'Generate structured study notes with key concepts, detailed explanations, and glossary.';
    }

    // Populate Tab 4: Quiz
    if (state.quiz && state.quiz.length > 0) {
        renderQuizView(state.quiz);
    } else {
        document.getElementById('quiz-empty-state').style.display = 'block';
        document.getElementById('quiz-content').style.display = 'none';
        document.getElementById('btn-gen-quiz').style.display = 'inline-flex';
        document.getElementById('quiz-empty-text').textContent = 'Generate an interactive 10-question multiple-choice quiz strictly grounded in the transcript.';
    }

    // Populate Tab 5: Chat
    document.getElementById('chat-empty-state').style.display = 'none';
    document.getElementById('chat-content').style.display = 'flex';
    document.getElementById('chat-messages').innerHTML = `
        <div id="chat-suggestions" class="clean-card" style="background-color: var(--bg-surface); padding: 16px;">
            <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px;">Suggested Questions to Ask:</div>
            <div style="display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #525252;">
                <span style="cursor: pointer;" onclick="askPreset('What are the main concepts covered in this video?')">• <i>What are the main concepts covered in this video?</i></span>
                <span style="cursor: pointer;" onclick="askPreset('Can you explain the key theory or technique mentioned?')">• <i>Can you explain the key theory or technique mentioned?</i></span>
                <span style="cursor: pointer;" onclick="askPreset('are there any battles in history which took place in the same year in which battle of plassey took place')">• <i>are there any battles in history which took place in the same year in which battle of plassey took place</i></span>
            </div>
        </div>
    `;

    // Switch to Transcript Tab
    switchTab('transcript');
}

// --- Transcript Explorer ---
function setTranscriptMode(mode) {
    state.transcriptMode = mode;
    document.getElementById('mode-btn-continuous').classList.toggle('active', mode === 'continuous');
    document.getElementById('mode-btn-timestamped').classList.toggle('active', mode === 'timestamped');
    renderTranscript();
}

function renderTranscript() {
    const box = document.getElementById('transcript-scrollbox');
    const query = (document.getElementById('transcript-filter-input').value || '').trim().toLowerCase();
    const sourceText = state.transcriptMode === 'continuous' ? state.clean_transcript : state.timestamped_transcript;

    if (!query) {
        box.textContent = sourceText;
        return;
    }

    const lines = sourceText.split('\n');
    const filtered = lines.filter(line => line.toLowerCase().includes(query));
    if (filtered.length > 0) {
        box.textContent = filtered.join('\n\n');
    } else {
        box.textContent = `No matches found for "${query}".`;
    }
}

function filterTranscript() {
    renderTranscript();
}

// --- Summary Generation & Copying ---
async function generateSummary() {
    if (!state.clean_transcript) return;
    const summaryMarkdown = document.getElementById('summary-markdown');
    
    document.getElementById('summary-empty-state').style.display = 'none';
    document.getElementById('summary-content').style.display = 'block';
    summaryMarkdown.innerHTML = '<div style="padding: 24px; text-align: center;"><span class="spinner-border-sm" style="border-color: #000000; border-right-color: transparent;"></span> Generating comprehensive summary...</div>';

    const data = await safeFetchJson('/api/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            video_id: state.video_id,
            transcript: state.clean_transcript,
            model: state.settings.ollama_model,
            host: state.settings.ollama_host
        })
    });

    if (data.success) {
        state.summary = data.summary;
        showSummaryView(data.summary);
    } else {
        summaryMarkdown.innerHTML = `<div style="color: #ef4444;">Error: ${data.error || 'Failed to generate summary.'}</div>`;
    }
}

function showSummaryView(markdown) {
    document.getElementById('summary-empty-state').style.display = 'none';
    document.getElementById('summary-content').style.display = 'block';
    document.getElementById('summary-markdown').innerHTML = marked.parse(markdown);
}

// Strips markdown symbols for plain text copying
function stripMarkdown(md) {
    if (!md) return '';
    return md
        .replace(/^#+\s+/gm, '')
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/\[(.*?)\]\((.*?)\)/g, '$1 ($2)')
        .replace(/^\s*[-*+]\s+/gm, '• ')
        .replace(/`{1,3}(.*?)`{1,3}/g, '$1')
        .trim();
}

async function copySummary(format = 'md') {
    if (!state.summary) return;
    const textToCopy = format === 'txt' ? stripMarkdown(state.summary) : state.summary;
    const btnId = format === 'txt' ? 'btn-copy-summary-txt' : 'btn-copy-summary-md';
    const btn = document.getElementById(btnId);

    try {
        await navigator.clipboard.writeText(textToCopy);
        if (btn) {
            const orig = btn.innerHTML;
            btn.innerHTML = '<span>✓ Copied!</span>';
            setTimeout(() => { btn.innerHTML = orig; }, 2000);
        }
    } catch (err) {
        alert('Failed to copy: ' + err);
    }
}

// --- Notes Generation & Copying ---
async function generateNotes() {
    if (!state.clean_transcript) return;
    const notesMarkdown = document.getElementById('notes-markdown');
    
    document.getElementById('notes-empty-state').style.display = 'none';
    document.getElementById('notes-content').style.display = 'block';
    notesMarkdown.innerHTML = '<div style="padding: 24px; text-align: center;"><span class="spinner-border-sm" style="border-color: #000000; border-right-color: transparent;"></span> Generating textbook study notes...</div>';

    const data = await safeFetchJson('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            video_id: state.video_id,
            transcript: state.clean_transcript,
            model: state.settings.ollama_model,
            host: state.settings.ollama_host
        })
    });

    if (data.success) {
        state.notes = data.notes;
        showNotesView(data.notes);
    } else {
        notesMarkdown.innerHTML = `<div style="color: #ef4444;">Error: ${data.error || 'Failed to generate notes.'}</div>`;
    }
}

function showNotesView(markdown) {
    document.getElementById('notes-empty-state').style.display = 'none';
    document.getElementById('notes-content').style.display = 'block';
    document.getElementById('notes-markdown').innerHTML = marked.parse(markdown);
}

async function copyNotes(format = 'md') {
    if (!state.notes) return;
    const textToCopy = format === 'txt' ? stripMarkdown(state.notes) : state.notes;
    const btnId = format === 'txt' ? 'btn-copy-notes-txt' : 'btn-copy-notes-md';
    const btn = document.getElementById(btnId);

    try {
        await navigator.clipboard.writeText(textToCopy);
        if (btn) {
            const orig = btn.innerHTML;
            btn.innerHTML = '<span>✓ Copied!</span>';
            setTimeout(() => { btn.innerHTML = orig; }, 2000);
        }
    } catch (err) {
        alert('Failed to copy: ' + err);
    }
}

// --- Quiz Component ---
async function generateQuiz() {
    if (!state.clean_transcript) return;
    const list = document.getElementById('quiz-questions-list');
    
    document.getElementById('quiz-empty-state').style.display = 'none';
    document.getElementById('quiz-content').style.display = 'block';
    document.getElementById('quiz-score-banner').style.display = 'none';
    list.innerHTML = '<div style="padding: 30px; text-align: center;"><span class="spinner-border-sm" style="border-color: #000000; border-right-color: transparent;"></span> Generating 10-question comprehension quiz...</div>';

    const data = await safeFetchJson('/api/quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            video_id: state.video_id,
            transcript: state.clean_transcript,
            model: state.settings.ollama_model,
            host: state.settings.ollama_host
        })
    });

    if (data.success && data.questions) {
        state.quiz = data.questions;
        renderQuizView(data.questions);
    } else {
        list.innerHTML = `<div style="color: #ef4444;">Error: ${data.error || 'Failed to generate quiz.'}</div>`;
    }
}

function renderQuizView(questions) {
    state.quizSubmitted = false;
    state.userAnswers = {};
    document.getElementById('quiz-empty-state').style.display = 'none';
    document.getElementById('quiz-content').style.display = 'block';
    document.getElementById('quiz-score-banner').style.display = 'none';
    document.getElementById('btn-submit-quiz').style.display = 'inline-flex';

    const list = document.getElementById('quiz-questions-list');
    list.innerHTML = '';

    questions.forEach((q, qIdx) => {
        const card = document.createElement('div');
        card.className = 'quiz-question-card';
        card.id = `quiz-card-${qIdx}`;

        const title = document.createElement('div');
        title.className = 'quiz-question-title';
        title.textContent = `${qIdx + 1}. ${q.question}`;
        card.appendChild(title);

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'quiz-options';

        q.options.forEach((optText, optIdx) => {
            const label = document.createElement('label');
            label.className = 'quiz-option-label';
            label.id = `opt-label-${qIdx}-${optIdx}`;

            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = `quiz_q_${qIdx}`;
            radio.value = optIdx;
            // CRITICAL: All start UNCHECKED (empty)
            radio.checked = false;

            radio.onchange = () => {
                state.userAnswers[qIdx] = optIdx;
            };

            const span = document.createElement('span');
            span.textContent = optText;

            label.appendChild(radio);
            label.appendChild(span);
            optionsDiv.appendChild(label);
        });

        card.appendChild(optionsDiv);

        // Explanation container (hidden initially)
        const expBox = document.createElement('div');
        expBox.id = `quiz-exp-${qIdx}`;
        expBox.style.display = 'none';
        card.appendChild(expBox);

        list.appendChild(card);
    });
}

function submitQuiz() {
    if (!state.quiz || state.quiz.length === 0) return;
    
    const answeredCount = Object.keys(state.userAnswers).length;
    if (answeredCount === 0) {
        alert('Please answer at least one question before submitting.');
        return;
    }

    let score = 0;
    state.quiz.forEach((q, qIdx) => {
        const userChoice = state.userAnswers[qIdx];
        const isCorrect = userChoice === q.correct_answer;
        if (isCorrect) score++;

        const expBox = document.getElementById(`quiz-exp-${qIdx}`);
        expBox.style.display = 'block';
        expBox.className = `quiz-explanation-box ${isCorrect ? 'correct' : 'incorrect'}`;
        expBox.innerHTML = `
            <strong>${isCorrect ? '✓ Correct!' : '✗ Incorrect.'}</strong> 
            (Correct Answer: Option ${String.fromCharCode(65 + q.correct_answer)}: ${q.options[q.correct_answer]})<br>
            <span style="font-size: 12px; margin-top: 4px; display: block;">${q.explanation}</span>
        `;

        // Highlight correct and incorrect options
        q.options.forEach((_, optIdx) => {
            const label = document.getElementById(`opt-label-${qIdx}-${optIdx}`);
            if (optIdx === q.correct_answer) {
                label.style.borderColor = '#16a34a';
                label.style.backgroundColor = '#f0fdf4';
            } else if (optIdx === userChoice) {
                label.style.borderColor = '#dc2626';
                label.style.backgroundColor = '#fef2f2';
            }
        });
    });

    state.quizSubmitted = true;
    document.getElementById('btn-submit-quiz').style.display = 'none';

    // Show score banner
    const banner = document.getElementById('quiz-score-banner');
    banner.style.display = 'flex';
    const percent = Math.round((score / state.quiz.length) * 100);
    document.getElementById('quiz-score-title').textContent = `Score: ${score} / ${state.quiz.length} (${percent}%)`;
    banner.scrollIntoView({ behavior: 'smooth' });
}

function retakeQuiz() {
    if (state.quiz) {
        renderQuizView(state.quiz);
    }
}

// --- Interactive Chat Component ---
function setChatMode(mode) {
    state.chatMode = mode;
    updateChatModeUI();
}

function updateChatModeUI() {
    const isWeb = state.chatMode === 'Video + Web Research';
    document.getElementById('chat-mode-web').classList.toggle('active', isWeb);
    document.getElementById('chat-mode-video').classList.toggle('active', !isWeb);
    document.getElementById('chat-mode-desc').textContent = isWeb 
        ? 'Automatic DuckDuckGo research enabled'
        : 'Answers strictly from transcript';
}

function clearChat() {
    state.chatHistory = [];
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div id="chat-suggestions" class="clean-card" style="background-color: var(--bg-surface); padding: 16px;">
            <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px;">Suggested Questions to Ask:</div>
            <div style="display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #525252;">
                <span style="cursor: pointer;" onclick="askPreset('What are the main concepts covered in this video?')">• <i>What are the main concepts covered in this video?</i></span>
                <span style="cursor: pointer;" onclick="askPreset('Can you explain the key theory or technique mentioned?')">• <i>Can you explain the key theory or technique mentioned?</i></span>
                <span style="cursor: pointer;" onclick="askPreset('are there any battles in history which took place in the same year in which battle of plassey took place')">• <i>are there any battles in history which took place in the same year in which battle of plassey took place</i></span>
            </div>
        </div>
    `;
}

function askPreset(question) {
    document.getElementById('chat-user-input').value = question;
    handleSendChat(new Event('submit'));
}

async function handleSendChat(e) {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById('chat-user-input');
    const question = input.value.trim();
    if (!question) return;

    input.value = '';
    const suggestions = document.getElementById('chat-suggestions');
    if (suggestions) suggestions.remove();

    const messagesBox = document.getElementById('chat-messages');

    // Add user bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.textContent = question;
    messagesBox.appendChild(userBubble);

    // Add assistant placeholder
    const assistantBubble = document.createElement('div');
    assistantBubble.className = 'chat-bubble assistant';
    assistantBubble.innerHTML = `<span class="spinner-border-sm" style="border-color: #000000; border-right-color: transparent;"></span> ${state.chatMode === 'Video + Web Research' ? 'Searching & thinking...' : 'Thinking...'}`;
    messagesBox.appendChild(assistantBubble);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    // Send to backend API
    const data = await safeFetchJson('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question: question,
            transcript: state.clean_transcript,
            chat_history: state.chatHistory,
            mode: state.chatMode,
            model: state.settings.ollama_model,
            host: state.settings.ollama_host
        })
    });

    if (data.success) {
        state.chatHistory.push({ role: 'user', content: question });
        state.chatHistory.push({ role: 'assistant', content: data.answer });

        let citationsHtml = '';
        if (data.source_type === 'web' && data.search_results && data.search_results.length > 0) {
            const listItems = data.search_results.map(r => 
                `<li style="margin-bottom: 6px;"><a href="${r.url}" target="_blank" rel="noopener noreferrer"><strong>${r.title}</strong></a><div style="font-size: 11px; color: #737373;">${r.snippet ? r.snippet.substring(0, 140) + '...' : ''}</div></li>`
            ).join('');

            citationsHtml = `
                <div style="font-size: 11px; font-weight: 600; color: #000000; margin-top: 10px;">
                    <i class="bi bi-journal-text"></i> Additional web research used
                </div>
                <details class="chat-sources-accordion" style="margin-top: 6px; cursor: pointer;">
                    <summary style="color: #737373; font-size: 12px; outline: none;">View Web Sources & Citations (${data.search_results.length})</summary>
                    <ul style="margin: 8px 0 0 16px; padding: 0;">${listItems}</ul>
                </details>
            `;
        } else {
            citationsHtml = `
                <div style="font-size: 11px; color: #737373; margin-top: 10px;">
                    <i class="bi bi-journal-text"></i> Video Transcript Grounding
                </div>
            `;
        }

        assistantBubble.innerHTML = `
            <div class="markdown-body">${marked.parse(data.answer)}</div>
            ${citationsHtml}
        `;
    } else {
        assistantBubble.innerHTML = `<div style="color: #ef4444;">⚠️ ${data.error || 'Failed to generate answer.'}</div>`;
    }

    messagesBox.scrollTop = messagesBox.scrollHeight;
}

// --- Study History View ---
async function loadHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = '<div style="padding: 24px; text-align: center;"><span class="spinner-border-sm" style="border-color: #000000; border-right-color: transparent;"></span> Loading saved sessions...</div>';

    const data = await safeFetchJson('/api/history');

    if (!data.sessions || data.sessions.length === 0) {
        list.innerHTML = `
            <div class="clean-card" style="text-align: center; padding: 36px;">
                <p style="color: var(--text-muted); margin: 0;">No past study sessions found. Process a video in <b>Study Session</b> to build your history.</p>
            </div>
        `;
        return;
    }

    list.innerHTML = '';
    data.sessions.forEach(s => {
        const card = document.createElement('div');
        card.className = 'history-card';

        const badges = [];
        if (s.has_summary) badges.push('<i class="bi bi-pencil-square"></i> Summary');
        if (s.has_notes) badges.push('<i class="bi bi-stickies"></i> Notes');
        if (s.has_quiz) badges.push('<i class="bi bi-ui-checks-grid"></i> Quiz');
        const badgeStr = badges.length > 0 ? badges.join(' · ') : 'Transcript';

        card.innerHTML = `
            <div>
                <div style="font-weight: 600; font-size: 15px;">${s.title || `Video ${s.video_id}`}</div>
                <div class="history-badges">
                    <span>Saved: ${s.created_at ? s.created_at.substring(0, 10) : 'Recent'}</span>
                    <span>·</span>
                    <span>${badgeStr}</span>
                </div>
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn-black-pill" style="padding: 6px 18px; font-size: 13px;" onclick="openPastSession('${s.video_id}')">
                    <span>Open Session →</span>
                </button>
                <button class="btn-outline-pill" style="padding: 6px 14px; font-size: 13px;" onclick="deletePastSession('${s.video_id}')">
                    <span>Delete</span>
                </button>
            </div>
        `;
        list.appendChild(card);
    });
}

async function openPastSession(videoId) {
    const data = await safeFetchJson(`/api/history/${videoId}`);
    if (data.success) {
        populateSession(data);
        switchNav('session');
    } else {
        alert(data.error || 'Could not open past session.');
    }
}

async function deletePastSession(videoId) {
    if (!confirm('Are you sure you want to delete this study session?')) return;
    const data = await safeFetchJson(`/api/history/${videoId}`, { method: 'DELETE' });
    if (data.success) {
        loadHistory();
    } else {
        alert(data.error || 'Error deleting session.');
    }
}
