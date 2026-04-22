document.addEventListener("DOMContentLoaded", () => {
    loadBig16();       // fetch + populate
});

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