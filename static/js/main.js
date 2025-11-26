async function checkSpelling() {
    const text = document.getElementById("inputText").value;
    if (!text.trim()) return;

    showLoading(true);
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

        document.getElementById("correctedText").innerText = data.corrected_text || "";
        
        if (data.detected_lang) {
            const badge = document.getElementById("detectedLangBadge");
            badge.innerText = data.detected_lang;
            badge.className = `badge ${data.confidence > 0.8 ? 'bg-success' : 'bg-warning'}`;
        }
        
        if (data.confidence !== undefined) {
            document.getElementById("detectedConfidence").innerText = Number(data.confidence).toFixed(2);
        }

        renderSuggestions(data.suggestions);
        showResults();
    } catch (err) {
        console.error(err);
        alert("Error checking spelling. See console for details.");
    } finally {
        showLoading(false);
    }
}

async function checkPerSegment() {
    const text = document.getElementById("inputText").value.trim();
    if (!text) return;

    showLoading(true);
    const segments = text.split(/(?<=[.?!])\s+/);
    const resultsContainer = document.getElementById("suggestionList");
    resultsContainer.innerHTML = "";

    try {
        for (const seg of segments) {
            const fd = new FormData();
            fd.append("text", seg);
            fd.append("mode", document.getElementById("modeSelect").value);

            const res = await fetch("/check", { method: "POST", body: fd });
            const data = await res.json();

            const header = document.createElement("li");
            header.className = "list-group-item active mt-2 border-0 rounded";
            header.style.backgroundColor = "var(--primary-color)";
            header.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span><strong>Segment</strong>: ${seg.substring(0, 50)}${seg.length > 50 ? '...' : ''}</span>
                    <span class="badge bg-light text-dark">${data.detected_lang || "und"}</span>
                </div>`;
            resultsContainer.appendChild(header);

            if (data.suggestions && Object.keys(data.suggestions).length) {
                for (const [w, cands] of Object.entries(data.suggestions)) {
                    addSuggestionItem(resultsContainer, w, cands);
                }
            } else {
                const li = document.createElement("li");
                li.className = "list-group-item text-muted fst-italic";
                li.innerText = "No suggestions for this segment.";
                resultsContainer.appendChild(li);
            }
        }
        showResults();
    } catch (err) {
        console.error("Segment check error", err);
    } finally {
        showLoading(false);
    }
}

async function checkMultipleLanguages() {
    const text = document.getElementById("inputText").value;
    if (!text) return;
    
    const selected = Array.from(document.getElementById("langSelect").selectedOptions).map(o => o.value);
    if (selected.length === 0) {
        alert("Select one or more languages to compare.");
        return;
    }

    showLoading(true);
    const resultsContainer = document.getElementById("suggestionList");
    resultsContainer.innerHTML = "";

    try {
        const promises = selected.map(lang => {
            const fd = new FormData();
            fd.append("text", text);
            if (lang !== "und") fd.append("lang", lang);
            fd.append("mode", document.getElementById("modeSelect").value);
            return fetch("/check", { method: "POST", body: fd }).then(r => r.json()).then(data => ({lang, data}));
        });

        const results = await Promise.all(promises);
        
        for (const {lang, data} of results) {
            const sec = document.createElement("li");
            sec.className = "list-group-item active mt-2 border-0 rounded";
            sec.style.backgroundColor = "var(--secondary-color)";
            sec.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span><strong>Language:</strong> ${lang}</span>
                    <small class="text-light">Detected: ${data.detected_lang || 'und'} (${Number(data.confidence||0).toFixed(2)})</small>
                </div>`;
            resultsContainer.appendChild(sec);

            if (data.suggestions && Object.keys(data.suggestions).length) {
                for (const [w, cands] of Object.entries(data.suggestions)) {
                    addSuggestionItem(resultsContainer, w, cands);
                }
            } else {
                const li = document.createElement("li");
                li.className = "list-group-item text-muted fst-italic";
                li.innerText = "No suggestions";
                resultsContainer.appendChild(li);
            }
        }
        showResults();
    } catch (err) {
        console.error(err);
    } finally {
        showLoading(false);
    }
}

function renderSuggestions(suggestions) {
    const suggestionList = document.getElementById("suggestionList");
    suggestionList.innerHTML = "";

    if (!suggestions || Object.keys(suggestions).length === 0) {
        const li = document.createElement("li");
        li.className = "list-group-item text-center text-muted py-4";
        li.innerHTML = "<i class='bi bi-check-circle display-4 d-block mb-2'></i>No spelling errors found!";
        suggestionList.appendChild(li);
        return;
    }

    for (const [word, candidates] of Object.entries(suggestions)) {
        addSuggestionItem(suggestionList, word, candidates);
    }
}

function addSuggestionItem(container, word, candidates) {
    const li = document.createElement("li");
    li.className = "list-group-item suggestion-item fade-in";
    
    // Format candidates with language tags
    const candidateHtml = candidates.map(c => {
        if (typeof c === 'object' && c.word) {
            return `<span class="suggestion-word">${c.word} <small class="text-muted">(${c.lang})</small></span>`;
        }
        return c;
    }).join(", ");

    li.innerHTML = `
        <div class="row align-items-center">
            <div class="col-md-3">
                <span class="text-danger text-decoration-line-through fw-bold">${word}</span>
            </div>
            <div class="col-md-1 text-center text-muted">
                <i class="bi bi-arrow-right"></i>
            </div>
            <div class="col-md-8">
                <span class="suggestion text-success fw-bold">${candidateHtml}</span>
            </div>
        </div>`;
    container.appendChild(li);
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showResults() {
    document.getElementById('resultsArea').style.display = 'block';
    document.getElementById('resultsArea').scrollIntoView({ behavior: 'smooth' });
}

function clearAll() {
    document.getElementById('inputText').value = '';
    document.getElementById('correctedText').innerText = '';
    document.getElementById('suggestionList').innerHTML = '';
    document.getElementById('detectedLangBadge').innerText = 'und';
    document.getElementById('detectedLangBadge').className = 'badge bg-secondary';
    document.getElementById('detectedConfidence').innerText = '0.00';
    document.getElementById('resultsArea').style.display = 'none';
}
