let currentPopover = null;
let checkTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('editor');
    const placeholder = document.getElementById('placeholder');
    
    if (editor) {
        editor.addEventListener('input', () => {
            updateStats();
            handleInput();
            
            // Toggle placeholder
            if (editor.innerText.trim() === '') {
                placeholder.style.display = 'block';
            } else {
                placeholder.style.display = 'none';
            }
        });
        
        // Handle paste to strip formatting and trigger immediate check
        editor.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.originalEvent || e).clipboardData.getData('text/plain');
            document.execCommand('insertText', false, text);
            // Trigger check immediately after paste
            if (checkTimeout) clearTimeout(checkTimeout);
            checkTimeout = setTimeout(checkSpelling, 100);
        });
    }

    // Auto-reload logic
    let lastTimestamp = 0;
    setInterval(async () => {
        try {
            const res = await fetch('/last_update');
            const data = await res.json();
            if (lastTimestamp === 0) {
                lastTimestamp = data.timestamp;
            } else if (data.timestamp > lastTimestamp) {
                console.log("File change detected, reloading...");
                location.reload();
            }
        } catch (e) {
            console.error("Auto-reload check failed", e);
        }
    }, 1000);
});

function updateStats() {
    const text = document.getElementById('editor').innerText;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    document.getElementById('statsWordCount').innerText = `${words} words`;
    document.getElementById('statsCharCount').innerText = `${chars} chars`;
}

function handleInput() {
    if (checkTimeout) clearTimeout(checkTimeout);
    checkTimeout = setTimeout(checkSpelling, 300); // Debounce 300ms for faster feedback
}

async function checkSpelling() {
    const editor = document.getElementById("editor");
    const text = editor.innerText;
    
    if (!text.trim()) return;

    // Don't show loading overlay for live check to avoid interrupting typing
    // showLoading(true); 
    
    const formData = new FormData();
    formData.append("text", text);
    const mode = document.getElementById("modeSelect").value;
    formData.append("mode", mode);

    const langSelect = document.getElementById("langSelect");
    const selectedLangs = Array.from(langSelect.selectedOptions).map(o => o.value);
    if (selectedLangs.length > 0) {
        const lang = selectedLangs[0];
        if (lang !== "und") {
            formData.append("lang", lang);
        }
    }

    try {
        const res = await fetch("/check", { method: "POST", body: formData });
        const data = await res.json();

        // Update stats and badges
        if (data.detected_lang) {
            const badge = document.getElementById("detectedLangBadge");
            const container = document.getElementById("detectedLangContainer");
            badge.innerText = data.detected_lang;
            badge.className = `badge ${data.confidence > 0.8 ? 'bg-success' : 'bg-warning'}`;
            container.style.display = 'inline';
        }
        
        renderTokensPreservingCursor(data.tokens);

    } catch (err) {
        console.error(err);
    }
}

function renderTokensPreservingCursor(tokens) {
    const editor = document.getElementById("editor");
    const selection = window.getSelection();
    
    // Save cursor position relative to text content
    let start = 0;
    let end = 0;
    if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const preCaretRange = range.cloneRange();
        preCaretRange.selectNodeContents(editor);
        preCaretRange.setEnd(range.startContainer, range.startOffset);
        start = preCaretRange.toString().length;
        end = start + range.toString().length;
    }

    // Rebuild HTML
    let html = "";
    tokens.forEach((token, index) => {
        if (token.type === "word" && !token.is_valid) {
            // Escape HTML in token text
            const safeText = escapeHtml(token.text);
            const suggestions = JSON.stringify(token.suggestions).replace(/"/g, '&quot;');
            html += `<span class="misspelled" id="token-${index}" data-suggestions="${suggestions}" onclick="showSuggestionPopover(event, this)">${safeText}</span>`;
        } else {
            html += escapeHtml(token.text);
        }
    });
    
    editor.innerHTML = html;

    // Restore cursor
    restoreSelection(editor, start, end);
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function restoreSelection(containerEl, start, end) {
    const charIndex = { count: 0 };
    const range = document.createRange();
    range.setStart(containerEl, 0);
    range.collapse(true);
    
    const nodeStack = [containerEl];
    let node, foundStart = false, foundEnd = false;

    while (!foundEnd && (node = nodeStack.pop())) {
        if (node.nodeType === 3) {
            const nextCharIndex = charIndex.count + node.length;
            if (!foundStart && start >= charIndex.count && start <= nextCharIndex) {
                range.setStart(node, start - charIndex.count);
                foundStart = true;
            }
            if (foundStart && end >= charIndex.count && end <= nextCharIndex) {
                range.setEnd(node, end - charIndex.count);
                foundEnd = true;
            }
            charIndex.count = nextCharIndex;
        } else {
            let i = node.childNodes.length;
            while (i--) {
                nodeStack.push(node.childNodes[i]);
            }
        }
    }

    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
}

function showSuggestionPopover(event, element) {
    event.stopPropagation();
    
    // Close existing popover
    if (currentPopover) {
        currentPopover.dispose();
        currentPopover = null;
        document.querySelectorAll('.misspelled').forEach(el => el.classList.remove('active-error'));
    }

    element.classList.add('active-error');

    const suggestions = JSON.parse(element.dataset.suggestions || "[]");
    const popoverContent = document.createElement('div');
    popoverContent.className = "list-group list-group-flush p-0";

    if (suggestions.length === 0) {
        popoverContent.innerHTML = `<div class="p-3 text-muted small">No suggestions found</div>`;
    } else {
        suggestions.forEach(s => {
            const item = document.createElement('div');
            item.className = "suggestion-option";
            item.innerHTML = `
                <span class="suggestion-word">${s.word}</span>
                <span class="suggestion-lang">${s.lang}</span>
            `;
            item.onclick = () => applySuggestion(element, s.word);
            popoverContent.appendChild(item);
        });
    }
    
    // Add "Ignore" option
    const ignoreItem = document.createElement('div');
    ignoreItem.className = "suggestion-option text-muted";
    ignoreItem.innerHTML = `<span class="small">Ignore</span>`;
    ignoreItem.onclick = () => {
        element.classList.remove("misspelled", "active-error");
        // Replace span with text node
        const textNode = document.createTextNode(element.innerText);
        element.parentNode.replaceChild(textNode, element);
        if (currentPopover) currentPopover.dispose();
    };
    popoverContent.appendChild(ignoreItem);

    currentPopover = new bootstrap.Popover(element, {
        content: popoverContent,
        html: true,
        trigger: 'manual',
        placement: 'bottom',
        customClass: 'shadow-lg'
    });

    currentPopover.show();

    // Close on click outside
    const closeHandler = (e) => {
        if (!element.contains(e.target) && !document.querySelector('.popover')?.contains(e.target)) {
            if (currentPopover) {
                currentPopover.dispose();
                currentPopover = null;
                element.classList.remove('active-error');
            }
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 0);
}

function applySuggestion(element, newWord) {
    // Replace span with new text
    const textNode = document.createTextNode(newWord);
    element.parentNode.replaceChild(textNode, element);
    
    if (currentPopover) {
        currentPopover.dispose();
        currentPopover = null;
    }
    updateStats();
    // Trigger re-check
    checkSpelling();
}

function fixAll() {
    const misspelledElements = document.querySelectorAll('.misspelled');
    if (misspelledElements.length === 0) return;

    let fixedCount = 0;
    misspelledElements.forEach(el => {
        const suggestions = JSON.parse(el.dataset.suggestions || "[]");
        if (suggestions.length > 0) {
            const bestSuggestion = suggestions[0].word;
            const textNode = document.createTextNode(bestSuggestion);
            el.parentNode.replaceChild(textNode, el);
            fixedCount++;
        }
    });

    if (fixedCount > 0) {
        updateStats();
        // Trigger re-check to ensure everything is clean
        checkSpelling();
    }
}

function copyText() {
    const text = document.getElementById("editor").innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById("copyBtn");
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check"></i>';
        setTimeout(() => btn.innerHTML = originalHtml, 2000);
    });
}

function clearAll() {
    document.getElementById("editor").innerText = "";
    document.getElementById("placeholder").style.display = 'block';
    document.getElementById("statsWordCount").innerText = "0 words";
    document.getElementById("statsCharCount").innerText = "0 chars";
    document.getElementById("detectedLangContainer").style.display = "none";
}

// Placeholder functions
function checkPerSegment() {
    alert("Segment view is currently being updated. Please use the main check.");
}

function checkMultipleLanguages() {
    alert("Multi-language comparison is currently being updated. Please use the main check.");
}
