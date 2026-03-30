const start_month = 11;
const start_year = 2020;
var today_month = 0;
var today_year = 0;

const month_short = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const months = [];

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
                const monthIndex = (idx - 2) / 2;
                const monthHeader = monthHeaders[monthIndex];
                const monthName = monthHeader ? monthHeader.textContent : "Unknown";

                artistData.push({
                    month: monthName,
                    plays: parseInt(playsCell.textContent) || 0,
                    rank: parseInt(rankCell.textContent)
                });
            }
        });
    });
    if (!artistData.length) return;

    // Sort by month order
    artistData.sort((a,b) => a.month.localeCompare(b.month));

    const firstMonth = artistData[0].month;
    const lastMonth = artistData[artistData.length-1].month;
    const mostPlays = Math.max(...artistData.map(d=>d.plays));
    const numberOneSpots = artistData.filter(d=>d.rank === 1).length;
    const top50Percentage = ((artistData.length / months.length) * 100).toFixed(1) + "%";

    // Longest streak
    let longestStreak = 0, currentStreak = 0;
    artistData.forEach(d => {
        if(d.rank <= 50) {
            currentStreak++;
            if(currentStreak > longestStreak) longestStreak = currentStreak;
        } else {
            currentStreak = 0;
        }
    });

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
    const firstMonth = artistData[0].month;
    const lastMonth = artistData[artistData.length - 1].month;
    const maxPlays = Math.max(...artistData.map(d => d.plays));
    const numFirstPlace = artistData.filter(d => d.rank === 1).length;
    const top50Percent = ((artistData.length / months.length) * 100).toFixed(1) + "%";

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