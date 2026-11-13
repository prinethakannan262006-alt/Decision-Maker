// Decision Matrix & Quick Picks Interactive Engine

document.addEventListener("DOMContentLoaded", () => {
    // State management for Matrix
    let options = ["Option A", "Option B", "Option C"];
    let criteria = [
        { name: "Cost / Value", weight: 4 },
        { name: "Quality / Impact", weight: 5 },
        { name: "Ease of Execution", weight: 3 }
    ];
    let scores = {}; // { "Option A": { "Cost / Value": 8, ... } }
    let lastCalculatedResult = null;

    // Elements
    const optionsContainer = document.getElementById("optionsContainer");
    const criteriaContainer = document.getElementById("criteriaContainer");
    const addOptionBtn = document.getElementById("addOptionBtn");
    const addCriterionBtn = document.getElementById("addCriterionBtn");
    const matrixTableHead = document.getElementById("matrixTableHead");
    const matrixTableBody = document.getElementById("matrixTableBody");
    const calculateBtn = document.getElementById("calculateMatrixBtn");
    const matrixErrorBox = document.getElementById("matrixErrorBox");
    const resultsCard = document.getElementById("matrixResultsCard");
    const winnerNameEl = document.getElementById("winnerName");
    const winnerScoreEl = document.getElementById("winnerScore");
    const rankedResultsList = document.getElementById("rankedResultsList");
    const saveDecisionBtn = document.getElementById("saveDecisionBtn");
    const saveStatusBox = document.getElementById("saveStatusBox");

    // Quick Picks Elements
    const coinFlipBtn = document.getElementById("coinFlipBtn");
    const coinVisual = document.getElementById("coinVisual");
    const coinResultText = document.getElementById("coinResultText");

    const diceRollBtn = document.getElementById("diceRollBtn");
    const diceVisual = document.getElementById("diceVisual");
    const diceResultText = document.getElementById("diceResultText");
    const diceSidesSelect = document.getElementById("diceSidesSelect");

    const randomPickBtn = document.getElementById("randomPickBtn");
    const randomPickInput = document.getElementById("randomPickInput");
    const randomPickResult = document.getElementById("randomPickResult");

    // Initialize UI
    renderOptionsList();
    renderCriteriaList();
    renderMatrixTable();

    // ==========================================
    // OPTIONS & CRITERIA BUILDER
    // ==========================================
    function renderOptionsList() {
        if (!optionsContainer) return;
        optionsContainer.innerHTML = "";
        options.forEach((opt, idx) => {
            const row = document.createElement("div");
            row.className = "flex items-center space-x-2";
            row.innerHTML = `
                <input type="text" value="${opt}" data-idx="${idx}" class="opt-name-input flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:bg-white focus:border-indigo-500 focus:outline-none">
                <button type="button" data-idx="${idx}" class="remove-opt-btn p-2 text-slate-400 hover:text-rose-600 rounded-lg transition-colors ${options.length <= 2 ? 'invisible' : ''}" title="Remove option">
                    <i class="fa-solid fa-trash-can text-sm"></i>
                </button>
            `;
            optionsContainer.appendChild(row);
        });

        // Listeners for option edits & delete
        optionsContainer.querySelectorAll(".opt-name-input").forEach(input => {
            input.addEventListener("input", (e) => {
                const idx = parseInt(e.target.dataset.idx);
                options[idx] = e.target.value.trim() || `Option ${idx + 1}`;
                renderMatrixTable();
            });
        });

        optionsContainer.querySelectorAll(".remove-opt-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.currentTarget.dataset.idx);
                if (options.length > 2) {
                    options.splice(idx, 1);
                    renderOptionsList();
                    renderMatrixTable();
                }
            });
        });
    }

    if (addOptionBtn) {
        addOptionBtn.addEventListener("click", () => {
            const newName = `Option ${String.fromCharCode(65 + options.length)}`;
            options.push(newName);
            renderOptionsList();
            renderMatrixTable();
        });
    }

    function renderCriteriaList() {
        if (!criteriaContainer) return;
        criteriaContainer.innerHTML = "";
        criteria.forEach((crit, idx) => {
            const row = document.createElement("div");
            row.className = "p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2";
            row.innerHTML = `
                <div class="flex items-center space-x-2">
                    <input type="text" value="${crit.name}" data-idx="${idx}" class="crit-name-input flex-1 px-3 py-1.5 bg-white border border-slate-200 rounded-md text-sm font-medium focus:border-indigo-500 focus:outline-none">
                    <button type="button" data-idx="${idx}" class="remove-crit-btn p-1.5 text-slate-400 hover:text-rose-600 transition-colors ${criteria.length <= 1 ? 'invisible' : ''}" title="Remove criterion">
                        <i class="fa-solid fa-trash-can text-sm"></i>
                    </button>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-500">
                    <span>Importance Weight (1–5):</span>
                    <span class="font-bold text-indigo-600 text-sm" id="critWeightVal_${idx}">${crit.weight}</span>
                </div>
                <input type="range" min="1" max="5" step="1" value="${crit.weight}" data-idx="${idx}" class="crit-weight-slider w-full accent-indigo-600">
            `;
            criteriaContainer.appendChild(row);
        });

        criteriaContainer.querySelectorAll(".crit-name-input").forEach(input => {
            input.addEventListener("input", (e) => {
                const idx = parseInt(e.target.dataset.idx);
                criteria[idx].name = e.target.value.trim() || `Criterion ${idx + 1}`;
                renderMatrixTable();
            });
        });

        criteriaContainer.querySelectorAll(".crit-weight-slider").forEach(slider => {
            slider.addEventListener("input", (e) => {
                const idx = parseInt(e.target.dataset.idx);
                const val = parseInt(e.target.value);
                criteria[idx].weight = val;
                const valLabel = document.getElementById(`critWeightVal_${idx}`);
                if (valLabel) valLabel.textContent = val;
                renderMatrixTable();
            });
        });

        criteriaContainer.querySelectorAll(".remove-crit-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.currentTarget.dataset.idx);
                if (criteria.length > 1) {
                    criteria.splice(idx, 1);
                    renderCriteriaList();
                    renderMatrixTable();
                }
            });
        });
    }

    if (addCriterionBtn) {
        addCriterionBtn.addEventListener("click", () => {
            criteria.push({ name: `Criterion ${criteria.length + 1}`, weight: 3 });
            renderCriteriaList();
            renderMatrixTable();
        });
    }

    // ==========================================
    // MATRIX TABLE GRID
    // ==========================================
    function renderMatrixTable() {
        if (!matrixTableHead || !matrixTableBody) return;

        // Build Table Header
        let thHtml = `<th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 bg-slate-50 sticky left-0 z-10 border-b border-slate-200">Options</th>`;
        criteria.forEach(crit => {
            thHtml += `
                <th class="px-4 py-3 text-center text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200 min-w-[130px]">
                    <div class="font-bold text-slate-900">${crit.name}</div>
                    <div class="text-[10px] text-indigo-600 font-semibold mt-0.5">Weight: ${crit.weight}x</div>
                </th>
            `;
        });
        matrixTableHead.innerHTML = `<tr>${thHtml}</tr>`;

        // Build Table Body
        let tbHtml = "";
        options.forEach(opt => {
            tbHtml += `<tr class="border-b border-slate-100 hover:bg-slate-50/50">`;
            tbHtml += `<td class="px-4 py-3 text-sm font-semibold text-slate-900 bg-white sticky left-0 z-10 shadow-sm border-r border-slate-100">${opt}</td>`;

            criteria.forEach(crit => {
                const currentScore = (scores[opt] && scores[opt][crit.name]) ? scores[opt][crit.name] : 5;
                tbHtml += `
                    <td class="px-4 py-2.5 text-center">
                        <div class="flex items-center justify-center space-x-1.5">
                            <input type="number" min="1" max="10" value="${currentScore}"
                                data-option="${opt}" data-criterion="${crit.name}"
                                class="matrix-score-input w-16 px-2 py-1 text-center font-bold text-slate-800 bg-slate-50 border border-slate-200 rounded-md focus:bg-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm">
                            <span class="text-xs text-slate-400">/10</span>
                        </div>
                    </td>
                `;
            });
            tbHtml += `</tr>`;
        });
        matrixTableBody.innerHTML = tbHtml;

        // Attach input listeners
        matrixTableBody.querySelectorAll(".matrix-score-input").forEach(input => {
            input.addEventListener("input", (e) => {
                const opt = e.target.dataset.option;
                const crit = e.target.dataset.criterion;
                let val = parseInt(e.target.value);
                if (isNaN(val)) val = 5;
                val = Math.max(1, Math.min(10, val));
                if (!scores[opt]) scores[opt] = {};
                scores[opt][crit] = val;
            });
        });
    }

    // ==========================================
    // MATRIX CALCULATION & SAVING
    // ==========================================
    if (calculateBtn) {
        calculateBtn.addEventListener("click", async () => {
            matrixErrorBox.classList.add("hidden");
            matrixErrorBox.textContent = "";

            // Gather current score state
            matrixTableBody.querySelectorAll(".matrix-score-input").forEach(input => {
                const opt = input.dataset.option;
                const crit = input.dataset.criterion;
                let val = parseInt(input.value);
                if (isNaN(val)) val = 5;
                if (!scores[opt]) scores[opt] = {};
                scores[opt][crit] = val;
            });

            calculateBtn.disabled = true;
            calculateBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i>Computing Ranks...`;

            try {
                const response = await fetch("/api/matrix/calculate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        options: options,
                        criteria: criteria,
                        scores: scores
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    matrixErrorBox.classList.remove("hidden");
                    matrixErrorBox.innerHTML = `
                        <strong>Error ${data.error_code || '400'}:</strong> ${data.error || 'Failed to calculate.'}<br>
                        <span class="text-xs">${data.suggested_fix || ''}</span>
                    `;
                    return;
                }

                // Render Results
                lastCalculatedResult = data;
                winnerNameEl.textContent = data.winner;
                winnerScoreEl.textContent = `Score: ${data.winner_score} pts`;

                rankedResultsList.innerHTML = "";
                data.results.forEach((res, idx) => {
                    const isWinner = idx === 0;
                    const card = document.createElement("div");
                    card.className = `p-4 rounded-xl border ${isWinner ? 'bg-indigo-50/80 border-indigo-200' : 'bg-slate-50 border-slate-200'} space-y-2`;
                    
                    let breakdownHtml = "";
                    res.breakdown.forEach(b => {
                        breakdownHtml += `
                            <span class="inline-block text-xs bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600 mr-1.5 mb-1">
                                ${b.criterion}: <strong>${b.raw_score}</strong> × ${b.weight} = <strong class="text-indigo-600">${b.weighted_contrib}</strong>
                            </span>
                        `;
                    });

                    card.innerHTML = `
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-2">
                                <span class="w-6 h-6 rounded-full ${isWinner ? 'bg-indigo-600 text-white' : 'bg-slate-300 text-slate-700'} flex items-center justify-center text-xs font-bold">
                                    #${idx + 1}
                                </span>
                                <span class="font-bold text-slate-900">${res.option}</span>
                                ${isWinner ? '<span class="text-xs font-bold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full uppercase">Winner</span>' : ''}
                            </div>
                            <span class="font-mono font-extrabold text-indigo-700 text-base">${res.total_score} pts</span>
                        </div>
                        <div class="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                            <div class="bg-indigo-600 h-full rounded-full transition-all duration-500" style="width: ${res.normalized_score}%"></div>
                        </div>
                        <div class="text-xs text-slate-500 pt-1">
                            ${breakdownHtml}
                        </div>
                    `;
                    rankedResultsList.appendChild(card);
                });

                resultsCard.classList.remove("hidden");
                resultsCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

            } catch (err) {
                matrixErrorBox.classList.remove("hidden");
                matrixErrorBox.textContent = "Network error calculating matrix. Please try again.";
            } finally {
                calculateBtn.disabled = false;
                calculateBtn.innerHTML = `<i class="fa-solid fa-calculator mr-2"></i>Calculate Ranked Results`;
            }
        });
    }

    if (saveDecisionBtn) {
        saveDecisionBtn.addEventListener("click", async () => {
            if (!lastCalculatedResult) return;

            const decisionTitle = prompt("Enter a title for this decision:", "My Decision Matrix Evaluation");
            if (!decisionTitle) return;

            saveDecisionBtn.disabled = true;
            saveDecisionBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i>Saving...`;

            try {
                const response = await fetch("/api/matrix/save", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        title: decisionTitle,
                        options: options,
                        criteria: criteria,
                        scores: scores,
                        winner: lastCalculatedResult.winner,
                        total_score: lastCalculatedResult.winner_score
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    saveStatusBox.classList.remove("hidden");
                    saveStatusBox.className = "p-3 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-medium";
                    saveStatusBox.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5"></i>${data.message}`;
                    setTimeout(() => saveStatusBox.classList.add("hidden"), 5000);
                } else {
                    alert("Error saving: " + (data.error || "Could not save decision."));
                }
            } catch (err) {
                alert("Network error saving decision to database.");
            } finally {
                saveDecisionBtn.disabled = false;
                saveDecisionBtn.innerHTML = `<i class="fa-solid fa-floppy-disk mr-2"></i>Save to SQL Database`;
            }
        });
    }

    // ==========================================
    // QUICK PICKS (Coin, Dice, Random Pick)
    // ==========================================
    if (coinFlipBtn && coinVisual) {
        coinFlipBtn.addEventListener("click", async () => {
            coinFlipBtn.disabled = true;
            coinVisual.classList.add("anim-coin-flipping");
            coinResultText.textContent = "Flipping...";

            try {
                const res = await fetch("/api/quick-picks/coin-flip");
                const data = await res.json();
                setTimeout(() => {
                    coinVisual.classList.remove("anim-coin-flipping");
                    coinVisual.textContent = data.result === "Heads" ? "🪙 H" : "🪙 T";
                    coinResultText.textContent = `${data.result}!`;
                    coinFlipBtn.disabled = false;
                }, 1000);
            } catch (e) {
                coinVisual.classList.remove("anim-coin-flipping");
                coinFlipBtn.disabled = false;
            }
        });
    }

    if (diceRollBtn && diceVisual) {
        diceRollBtn.addEventListener("click", async () => {
            diceRollBtn.disabled = true;
            diceVisual.classList.add("anim-dice-rolling");
            diceResultText.textContent = "Rolling...";

            const sides = diceSidesSelect ? diceSidesSelect.value : 6;
            try {
                const res = await fetch(`/api/quick-picks/dice-roll?sides=${sides}`);
                const data = await res.json();
                setTimeout(() => {
                    diceVisual.classList.remove("anim-dice-rolling");
                    diceVisual.textContent = data.result;
                    diceResultText.textContent = `Rolled: ${data.result}`;
                    diceRollBtn.disabled = false;
                }, 800);
            } catch (e) {
                diceVisual.classList.remove("anim-dice-rolling");
                diceRollBtn.disabled = false;
            }
        });
    }

    if (randomPickBtn && randomPickInput && randomPickResult) {
        randomPickBtn.addEventListener("click", async () => {
            const raw = randomPickInput.value.trim();
            const items = raw.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);

            if (items.length < 2) {
                alert("Please enter at least 2 items (separated by commas or new lines).");
                return;
            }

            randomPickBtn.disabled = true;
            randomPickResult.textContent = "Selecting...";

            try {
                const res = await fetch("/api/quick-picks/random-choice", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ items: items })
                });
                const data = await res.json();
                if (res.ok) {
                    randomPickResult.innerHTML = `
                        <div class="text-xs uppercase tracking-wide text-indigo-500 font-bold mb-1">Random Pick Winner</div>
                        <div class="text-2xl font-black text-slate-900">${data.result}</div>
                    `;
                } else {
                    alert(data.error || "Failed to make random pick.");
                }
            } catch (e) {
                alert("Network error.");
            } finally {
                randomPickBtn.disabled = false;
            }
        });
    }
});
