/**
 * BUGS
 * Big 16 List (1) (2) (3) should not be movable, shouldn't be able to put song before rank
 * Big 16 List placing a new song on top of another in a slot should move the old one back to the candidates
 * Default songs do not have monthly plays
 * When moving default song to candidates list, they become unmovable
 * And I want to make the first slot golden
 * 
 */

document.addEventListener("DOMContentLoaded", () => {
    loadBig16(); // Top table
    buildBig16Slots(); // Creator
    initializeBig16(); // Creator
});

// Top table
async function loadBig16() {
    try {
        const res = await fetch("/api/big16");
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        const pivoted = pivotBig16(data);

        renderBig16Table(pivoted);
        enableCellExpansion();
    } catch (err) {
        console.error("Fetch failed: ", err);
    }
}

function pivotBig16(data) {
    const result = {};
    const months = [];

    data.forEach(row => {
        const yr = Number(row.Year);
        const mn = Number(row.Month);

        if (!yr || !mn) {
            console.warn("Bad row:", row);
            return;
        }

        const key = `${yr}-${String(mn).padStart(2, "0")}`;

        const date = new Date(yr, mn - 1);

        const label = date.toLocaleString("default", {
            month: "long",
            year: "numeric"
        });

        if (!months.find(m => m.key === key)) {
            months.push({ key, label });
        }

        if (!result[row.Rank]) {
            result[row.Rank] = { Rank: row.Rank };
        }

        result[row.Rank][`${key}_plays`] = row.Plays;
        result[row.Rank][`${key}_song`] = row.SongName;
        result[row.Rank][`${key}_artist`] = row.ArtistName;
    });

    months.sort((a, b) => a.key.localeCompare(b.key));

    return {
        rows: Object.values(result).sort((a, b) => a.Rank - b.Rank),
        months
    };
}

function renderBig16Table({ rows, months }) {
    const container = document.getElementById("big16-table");

    let html = "<table class='big16'><thead>";

    // 🔝 Top header row (months)
    html += "<tr>";
    html += "<th rowspan='2'>Rank</th>";

    months.forEach(m => {
        html += `<th colspan="3">${m.label}</th>`;
    });

    html += "</tr>";

    // 🔽 Second header row (sub-columns)
    html += "<tr>";

    months.forEach(() => {
        html += "<th>Plays</th>";
        html += "<th>Song</th>";
        html += "<th>Artist</th>";
    });

    html += "</tr>";

    html += "</thead><tbody>";

    // Rows (unchanged)
    rows.forEach(row => {
        html += "<tr>";
        html += `<td>${row.Rank}</td>`;

        months.forEach(m => {
            const plays = row[`${m.key}_plays`];

            html += `<td>${plays && plays !== 0 ? plays : ""}</td>`;
            html += `<td title="${row[`${m.key}_song`] ?? ""}">
                        ${row[`${m.key}_song`] ?? ""}
                    </td>`;

            html += `<td title="${row[`${m.key}_artist`] ?? ""}">
                        ${row[`${m.key}_artist`] ?? ""}
                    </td>`;
        });

        html += "</tr>";
    });

    html += "</tbody></table>";

    container.innerHTML = html;
}

function enableCellExpansion() {
    document.querySelectorAll(".big16 td").forEach(cell => {
        cell.addEventListener("click", () => {
            // toggle only for song/artist columns (skip rank + plays)
            const colIndex = cell.cellIndex;

            if (colIndex === 0) return; // skip Rank
            if ((colIndex - 1) % 3 === 0) return; // skip Plays

            cell.classList.toggle("expanded");
        });
    });
}

// Big 16 Creator
function initializeBig16() {
    loadCreator();

    const yearSelect = document.getElementById("yearSelect");
    const monthSelect = document.getElementById("monthSelect");

    const currentYear = new Date().getFullYear();

    for (let year = currentYear; year >= 2020; year--) {
        const option = document.createElement("option");
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }

    let year = currentYear;
    let month = new Date().getMonth();

    if (month === 0) {
        month = 12;
        year--;
    }

    yearSelect.value = year;
    monthSelect.value = month;

    refreshCandidates();

    yearSelect.addEventListener("change", refreshCandidates);
    monthSelect.addEventListener("change", refreshCandidates);
}

function loadCreator() {
    new Sortable(document.getElementById("candidateSongs"), {
        group: "songs",
        animation: 150
    });

    document.querySelectorAll(".big16-slot").forEach(slot => {
        new Sortable(slot, {
            group: "songs",
            animation: 150,
            swapThreshold: 0.5,
            onAdd() { slot.classList.remove("empty"); },
            onRemove() { if (!slot.querySelector(".song-item")) slot.classList.add("empty"); }
        });
    });
}

async function refreshCandidates() {

    const year = parseInt(document.getElementById("yearSelect").value);
    const month = parseInt(document.getElementById("monthSelect").value);

    buildBig16Slots();
    loadCreator();

    const res = await fetch(`/api/big16/init?year=${year}&month=${month}`);
    const data = await res.json();

    renderBig16(data.big16);
    renderCandidates(data.candidates);
}

function renderBig16(data) {
    data.forEach(song => {
        const slot = document.querySelector(`.big16-slot[data-rank="${song.Rank}"]`);
        if (!slot) return;

        slot.classList.remove("empty");

        const el = document.createElement("div");
        el.className = "song-item";
        el.dataset.songId = song.song_id;
        el.innerHTML =
            `${makeLink(song.artist_id, song.artist, "artist")} - ${makeLink(song.song_id, song.song, "song")}`;

        slot.appendChild(el);
    });
}

function renderCandidates(data) {
    const list = document.getElementById("candidateSongs");
    list.innerHTML = "";

    data.forEach(song => {
        const li = document.createElement("li");
        li.className = "song-item";
        li.dataset.songId = song.song_id;
        li.innerHTML =
            `${makeLink(song.artist_id, song.artist, "artist")} - ${makeLink(song.song_id, song.song, "song")} (${song.plays})`;

        list.appendChild(li);
    });
}

function buildBig16Slots() {
    const list = document.getElementById("big16List");
    list.innerHTML = "";

    for (let r = 1; r <= 16; r++) {
        const li = document.createElement("li");
        li.className = "big16-slot empty";
        li.dataset.rank = r;
        li.innerHTML = `<span class="rank">(${r})</span>`;
        list.appendChild(li);
    }
}

function saveBig16() {
    const songs = [];
    document.querySelectorAll(".big16-slot").forEach(slot => {
        const song = slot.querySelector(".song-item");
        if (!song) return;
        songs.push({ song_id: parseInt(song.dataset.songId), rank: parseInt(slot.dataset.rank) });
    });

    if (songs.length !== 16) { alert("Please fill all 16 Big 16 slots."); return; }

    fetch("/api/big16/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            year: parseInt(document.getElementById("yearSelect").value),
            month: parseInt(document.getElementById("monthSelect").value),
            songs
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) return alert(data.error);
        alert("Saved");
    })
    .catch(() => alert("Save failed"));
}