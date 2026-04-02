const start_month = 11;
const start_year = 2020;
var today_month = 0;
var today_year = 0;

const month_short = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const months = [];

// Summary table
let summarySort = {
    column: "percentTop50",
    direction: "desc"
};
let summaryData = [];
const summaryColumnMap = {
    "Artist": "artist",
    "First Month": "firstMonth",
    "Last Month": "lastMonth",
    "Most Plays": "mostPlays",
    "#1 Months": "numOnes",
    "% Top 50": "percentTop50",
    "Longest Streak": "longest"
};

// Send to start // end buttons
const tableContainer = document.querySelector(".table-container");
const table = document.getElementById("sheets-cup-table");
const artistStats = document.getElementById("artistStats");
const searchInput = document.getElementById("artist-search");
const scrollLeftBtn = document.getElementById("scroll-left");
const scrollRightBtn = document.getElementById("scroll-right");

document.addEventListener("DOMContentLoaded", () => {
    getDates();        // find current date
    loadData();       // fetch + populate
});

// ===== Scroll buttons =====
scrollLeftBtn.onclick = () => {
    tableContainer.scrollTo({ left: 0, behavior: "smooth" });
};
scrollRightBtn.onclick = () => {
    tableContainer.scrollTo({ left: tableContainer.scrollWidth, behavior: "smooth" });
};
document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") tableContainer.scrollLeft += 400;
    if (e.key === "ArrowLeft") tableContainer.scrollLeft -= 400;
    if (e.key === "ArrowUp") document.documentElement.scrollTop = 200;
});

// Reset stats helper
function resetStats() {
    artistStats.innerHTML = "";      // remove all stat boxes
    artistStats.classList.add("hidden"); // hide the container
}
// Exact match search
searchInput.addEventListener("input", () => {
    const term = searchInput.value.trim().toLowerCase();

    // Clear previous highlights
    table.querySelectorAll("td.highlight").forEach(td => td.classList.remove("highlight"));
    resetStats();

    if (!term) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));
    // Get all month headers from first row, skipping the Rank column
    const monthHeaders = Array.from(table.querySelectorAll("thead tr:first-child th")).slice(1);
    const artistData = [];
    rows.forEach(row => {
        const cells = row.querySelectorAll("td");
        cells.forEach((cell, idx) => {
            const cellText = cell.textContent.trim().toLowerCase();

            // Artist cells are at indices 2,4,6,... (0=Rank, 1=Plays Month1, 2=Artist Month1, 3=Plays Month2, 4=Artist Month2)
            if (idx >= 2 && idx % 2 === 0 && cellText === term) {
                cell.classList.add("highlight");

                const playsCell = cells[idx - 1];
                const rankCell = cells[0];

                // Since idx=2,4,6,... for artist columns
                const monthIndex = Math.floor((idx - 1) / 2); // adjust for Rank column
                const monthDate = months[monthIndex];
                const monthName = `${month_short[monthDate.getMonth()]} ${monthDate.getFullYear()}`;

                artistData.push({
                    month: monthName,
                    monthDate: monthDate,  // ✅ REAL DATE
                    plays: parseInt(playsCell.textContent) || 0,
                    rank: parseInt(rankCell.textContent)
                });
            }
        });
    });
    if (!artistData.length) return;

    // Sort by month order
    artistData.sort((a, b) => a.monthDate - b.monthDate);
    displayArtistStats(artistData);
});

function displayArtistStats(artistData) {
    artistStats.innerHTML = "";

    if (!artistData || !artistData.length) {
        artistStats.classList.add("hidden");
        return;
    }
    artistStats.classList.remove("hidden");

    // Compute stats
    const firstMonth = artistData.reduce((min, d) =>
        d.monthDate < min.monthDate ? d : min
    ).month;
    const lastMonth = artistData.reduce((max, d) =>
        d.monthDate > max.monthDate ? d : max
    ).month;
    const maxPlays = Math.max(...artistData.map(d => d.plays));
    const numFirstPlace = artistData.filter(d => d.rank === 1).length;

    const debutDate = artistData[0].monthDate;
    const monthsSinceDebut = months.filter(m => m >= debutDate).length;
    const top50Months = artistData.length;
    console.log(artistData);
    const top50Percent = monthsSinceDebut > 0 ? ((top50Months / monthsSinceDebut) * 100).toFixed(1) : 0;

    // Longest streak calculation
    let longestStreak = 0, currentStreak = 0;
    for (let i = 0; i < months.length; i++) {
        const monthStr = `${month_short[months[i].getMonth()]} ${months[i].getFullYear()}`;
        if (artistData.some(d => d.month === monthStr)) {
            currentStreak++;
            if (currentStreak > longestStreak) longestStreak = currentStreak;
        } else {
            currentStreak = 0;
        }
    }

    const stats = [
        { label: "First Month", value: firstMonth },
        { label: "Last Month", value: lastMonth },
        { label: "Most Plays", value: maxPlays },
        { label: "#1 Months", value: numFirstPlace },
        { label: "% Top 50", value: top50Percent },
        { label: "Longest Streak", value: longestStreak }
    ];

    stats.forEach(stat => {
        const statDiv = document.createElement("div");
        statDiv.classList.add("stat");

        const labelDiv = document.createElement("div");
        labelDiv.classList.add("label");
        labelDiv.textContent = stat.label;

        const valueDiv = document.createElement("div");
        valueDiv.classList.add("value");
        valueDiv.textContent = stat.value;

        statDiv.appendChild(labelDiv);
        statDiv.appendChild(valueDiv);

        artistStats.appendChild(statDiv);
    });
}

function getDates() {
    let today = new Date();
    today_month = today.getMonth();
    today_year = today.getFullYear();
    
    m = start_month;
    y = start_year;
    while (y <= today_year) {
        if (y == today_year && m > today_month) {
            break;
        }
        mnth = new Date();
        mnth.setHours(0);
        mnth.setFullYear(y, m, 1);
        months.push(mnth);
        m += 1
        if (m > 11) {
            y += 1
            m = 0
        }
    }
}

async function loadData() {
    try {
        const res = await fetch("/api/sheetscup");
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        const pivoted = pivotMonthlyData(data);

        renderTable();        // build structure
        renderRows(pivoted);  // fill data
        buildSummaryData();
        renderSummaryTable(); // build second table

    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

function renderTable() {
    const container = document.getElementById("sheets-cup-table");
    container.innerHTML = "";

    const table = document.createElement("table");
    table.classList.add("list-table");
    table.id = "sheets-cup-table";

    const thead = document.createElement("thead");

    // ===== ROW 1: Month labels =====
    const trMonth = document.createElement("tr");

    // Rank column (spans both rows)
    const rankTh = document.createElement("th");
    rankTh.textContent = "Rank";
    rankTh.rowSpan = 2;
    rankTh.classList.add("sticky-rank");
    trMonth.appendChild(rankTh);

    // Month headers
    months.forEach(h => {
        const th = document.createElement("th");
        th.colSpan = 2;
        th.textContent = `${month_short[h.getMonth()]} ${h.getFullYear()}`;
        trMonth.appendChild(th);
    });

    // ===== ROW 2: Plays / Artist =====
    const trSub = document.createElement("tr");

    months.forEach(() => {
        const playsTh = document.createElement("th");
        playsTh.textContent = "#";

        const artistTh = document.createElement("th");
        artistTh.textContent = "Artist";

        trSub.appendChild(playsTh);
        trSub.appendChild(artistTh);
    });

    thead.appendChild(trMonth);
    thead.appendChild(trSub);

    // ===== BODY =====
    const tbody = document.createElement("tbody");
    tbody.id = "artistTableBody";

    table.appendChild(thead);
    table.appendChild(tbody);
    container.appendChild(table);
}

function pivotMonthlyData(data) {
    const result = {};

    data.forEach(row => {
        const key = `${row.yr}-${row.mn}`;

        if (!result[key]) result[key] = [];

        result[key].push({
            artist: row.artist,
            plays: row.plays
        });
    });

    // sort each month by plays desc (just in case)
    Object.values(result).forEach(arr => {
        arr.sort((a, b) => b.plays - a.plays);
    });

    return result;
}

function renderRows(pivoted) {
    const tbody = document.getElementById("artistTableBody");
    tbody.innerHTML = "";

    const maxRank = 50;

    for (let i = 0; i < maxRank; i++) {
        const tr = document.createElement("tr");

        // Rank column
        tr.appendChild(tdCell(i + 1));

        months.forEach(h => {
            const key = `${h.getFullYear()}-${h.getMonth() + 1}`;
            const monthData = pivoted[key] || [];

            const entry = monthData[i];

            if (entry) {
                tr.appendChild(tdCell(entry.plays));
                tr.appendChild(tdCell(entry.artist));
            } else {
                tr.appendChild(tdCell(""));
                tr.appendChild(tdCell(""));
            }
        });

        tbody.appendChild(tr);
    }
}

function tdCell(content) {
    const cell = document.createElement("td");
    cell.textContent = content ?? "";
    return cell;
}

// Second Table
function buildAllArtistStats() {
    const table = document.getElementById("sheets-cup-table");
    const rows = Array.from(table.querySelectorAll("tbody tr"));

    const artistMap = {}; // { artistName: [ {monthDate, plays, rank} ] }

    rows.forEach(row => {
        const cells = row.querySelectorAll("td");
        const rank = parseInt(cells[0].textContent);

        cells.forEach((cell, idx) => {
            // artist columns (Rank | Plays | Artist | Plays | Artist ...)
            if (idx === 0 || idx % 2 === 1) return;

            const artist = cell.textContent.trim();
            if (!artist) return;

            const plays = parseInt(cells[idx - 1].textContent) || 0;

            const monthIndex = Math.floor((idx - 2) / 2);
            const monthDate = months[monthIndex];

            if (!artistMap[artist]) {
                artistMap[artist] = [];
            }
            artistMap[artist].push({
                monthDate,
                plays,
                rank
            });
        });
    });

    return artistMap;
}

function computeStats(entries) {
    // sort chronologically
    entries.sort((a, b) => a.monthDate - b.monthDate);

    const firstMonth = entries[0].monthDate;
    const lastMonth = entries[entries.length - 1].monthDate;

    const mostPlays = Math.max(...entries.map(e => e.plays));
    const numOnes = entries.filter(e => e.rank === 1).length;

    // % Top 50 (since debut)
    const monthsSinceDebut = months.filter(m => m >= firstMonth).length;
    const percentTop50 = monthsSinceDebut > 0
        ? ((entries.length / monthsSinceDebut) * 100).toFixed(1)
        : 0;

    // Longest streak
    let longest = 1;
    let current = 1;

    for (let i = 1; i < entries.length; i++) {
        const prev = entries[i - 1].monthDate;
        const curr = entries[i].monthDate;

        const diffMonths =
            (curr.getFullYear() - prev.getFullYear()) * 12 +
            (curr.getMonth() - prev.getMonth());

        if (diffMonths === 1) {
            current++;
            longest = Math.max(longest, current);
        } else {
            current = 1;
        }
    }

    return {
        firstMonth,
        lastMonth,
        mostPlays,
        numOnes,
        percentTop50,
        longest
    };
}

function buildSummaryData() {
    const artistMap = buildAllArtistStats();

    summaryData = Object.entries(artistMap).map(([artist, entries]) => {
        const stats = computeStats(entries);

        return {
            artist,
            mostPlays: stats.mostPlays,
            numOnes: stats.numOnes,
            percentTop50: parseFloat(stats.percentTop50),
            longest: stats.longest,
            firstMonth: stats.firstMonth,
            lastMonth: stats.lastMonth
        };
    });
}

function renderSummaryTable() {
    const container = document.getElementById("sheets-cup-summary");
    container.innerHTML = "";

    const table = document.createElement("table");
    table.classList.add("list-table");

    const headers = [
        "Rank", "Artist", "Most Plays", "#1 Months", "% Top 50",
        "Longest Streak", "First Month", "Last Month"
    ];

    // SORT
    sortSummaryData();

    // ===== HEADER =====
    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");

    headers.forEach(h => {
        const th = document.createElement("th");
        const key = summaryColumnMap[h];

        // Set label
        th.textContent = h;

        if (key) {
            th.style.cursor = "pointer";

            // Add arrow if active column
            if (summarySort.column === key) {
                th.textContent += summarySort.direction === "asc" ? " ▲" : " ▼";
            }

            th.onclick = () => {
                if (summarySort.column === key) {
                    summarySort.direction =
                        summarySort.direction === "asc" ? "desc" : "asc";
                } else {
                    summarySort.column = key;
                    summarySort.direction = "desc";
                }
 
                renderSummaryTable(); // re-render
            };
        }

        trHead.appendChild(th);
    });

    thead.appendChild(trHead);
    table.appendChild(thead);

    // ===== BODY =====
    const tbody = document.createElement("tbody");

    summaryData.forEach((a, i) => {
        const tr = document.createElement("tr");

        tr.appendChild(tdCell(i + 1));
        tr.appendChild(tdCell(a.artist));
        tr.appendChild(tdCell(a.mostPlays));
        tr.appendChild(tdCell(a.numOnes));
        tr.appendChild(tdCell(a.percentTop50 + "%"));
        tr.appendChild(tdCell(a.longest));
        tr.appendChild(tdCell(formatMonth(a.firstMonth)));
        tr.appendChild(tdCell(formatMonth(a.lastMonth)));

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}

function formatMonth(date) {
    return `${month_short[date.getMonth()]} ${date.getFullYear()}`;
}

function sortSummaryData() {
    const { column, direction } = summarySort;

    summaryData.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        // ✅ Explicit date handling (MOST IMPORTANT)
        if (valA instanceof Date && valB instanceof Date) {
            return direction === "asc"
                ? valA - valB
                : valB - valA;
        }

        // Strings
        if (typeof valA === "string") {
            return direction === "asc"
                ? valA.localeCompare(valB)
                : valB.localeCompare(valA);
        }

        // Numbers
        return direction === "asc"
            ? valA - valB
            : valB - valA;
    });
}