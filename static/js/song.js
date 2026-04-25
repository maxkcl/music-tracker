let showAllMonths = false;
let fullMonthlyData = [];

const CUTOFF_YEAR = 2020;
const CUTOFF_MONTH = 12; // December

document.addEventListener("DOMContentLoaded", () => {
    const el = document.querySelector(".song-page");

    if (!el) {
        console.error("song-page element not found");
        return;
    }

    const songId = el.dataset.songId;

    console.log("Song ID:", songId);

    loadSong(songId);
});

async function loadSong(songId) {
    try {
        const res = await fetch(`/api/song/${songId}`);

        const data = await res.json();
        const info = data.info[0];

        document.getElementById("song-name").innerHTML = `<h1>
                ${makeLink(info.ArtistID, info.ArtistName, "artist")}
                — 
                ${info.SongName}
            </h1>`;

        const res1 = await fetch(`/api/song/${songId}/monthly`);

        const text = await res1.text();

        if (!res1.ok) {
            throw new Error(`Monthly fetch failed: ${res1.status}`);
        }

        const data1 = JSON.parse(text);

        const trimmed = trimLeadingEmptyMonths(data1);

        fullMonthlyData = trimmed;

        renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));

    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

function renderMonthlyTable(data) {
    let html = "<table class='monthly'>";
    
    html += `
        <thead>
            <tr>
                <th>Month</th>
                <th>Rank</th>
                <th>Plays</th>
                <th>B16 Rank</th>
            </tr>
        </thead>
        <tbody>
    `;

    data.forEach(row => {
        const label = new Date(row.Year, row.Month - 1)
            .toLocaleString("default", { month: "short", year: "numeric" });
        
        const beforeCutoff = isBeforeCutoff(row.Year, row.Month);
        const plays = beforeCutoff ? "" : row.Plays;

        const isNumberOne = row.IsN1 === 1;

        html += `
            <tr>
                <td class="${isNumberOne ? "n1-row" : ""}">${label}</td>
                <td>${row.PlaysRank == null ? "": row.PlaysRank}</td>
                <td>${plays}</td>
                <td class="${isNumberOne ? "n1-row" : ""}">${row.Big16Rank == null ? "": row.Big16Rank}</td>
            </tr>
        `;
    });

    html += "</tbody></table>";

    document.getElementById("song-monthly").innerHTML = html;
}

function trimLeadingEmptyMonths(data) {
    const firstIndex = data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );

    // If no activity at all, just return original (or empty if you prefer)
    if (firstIndex === -1) return data;

    return data.slice(firstIndex);
}

function findFirstActiveIndex(data) {
    return data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );
}

function filterMonths(data, showAll) {
    const start = findFirstActiveIndex(data);

    if (start === -1) return data; // no activity at all

    const sliced = data.slice(start);

    if (showAll) return sliced;

    return sliced.filter(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );
}

function toggleMonths() {
    showAllMonths = !showAllMonths;

    const btn = document.getElementById("toggle-months-btn");
    btn.innerText = showAllMonths ? "Hide Empty Months" : "Show All Months";

    renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));
}

function isBeforeCutoff(year, month) {
    return (
        year < CUTOFF_YEAR ||
        (year === CUTOFF_YEAR && month < CUTOFF_MONTH)
    );
}