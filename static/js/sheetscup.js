const start_month = 11;
const start_year = 2020;
var today_month = 0;
var today_year = 0;

const month_short = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const months = [];

document.addEventListener("DOMContentLoaded", () => {
    getDates();        // find current date
    loadData();       // fetch + populate
});

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
    const container = document.getElementById("sheets-cup-results");
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
        playsTh.textContent = "Plays";

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