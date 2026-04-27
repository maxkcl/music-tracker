// ================================================================================================= //
//
//  song.js
//  - The logic of the individual song pages.
//
// ================================================================================================= //

let showAllMonths = false;
let fullMonthlyData = [];

// The cutoff is used to distinguish BEFORE and AFTER last.fm scrobbling began.
const CUTOFF_YEAR = 2020;
const CUTOFF_MONTH = 12; // December

// Page load
document.addEventListener("DOMContentLoaded", () => {
    
    // Fetch Song ID from HTML
    const el = document.querySelector(".song-page");
    if (!el) {
        console.error("song-page element not found");
        return;
    }
    const songId = el.dataset.songId;

    // Load data
    loadSong(songId);
});

// This function loads song data from the flask route and begins page rendering.
async function loadSong(songId) {
    try {
        const res = await fetch(`/api/song/${songId}`);
        const data = await res.json();

        // Renders the summary section of the page at the top.
        renderSongSummary(data.song);

        // Monthly data table. Months before data are trimmed and hidden.
        const trimmed = trimLeadingEmptyMonths(data.monthly);
        fullMonthlyData = trimmed;
        renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));
        
    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

// This function renders the summary section of the page at the top.
function renderSongSummary(data) {
        document.getElementById("song-name").innerHTML = `<h1>
                ${makeLink(data.ArtistID, data.ArtistName, "artist")}
                — 
                ${data.SongName}
            </h1>`;
}



// =
// ===
// ===== MONTHLY TABLE =====
// ===
// =

// This function renders the monthly data table displaying song statistics.
function renderMonthlyTable(data) {
    let html = "<table class='monthly'>";
    
    // HEADER //
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

    // BODY //
    data.forEach(row => {
        // Label is the month column.
        const label = new Date(row.Year, row.Month - 1)
            .toLocaleString("default", { month: "short", year: "numeric" });
        
        // Check if month is before December 2020 cutoff.
        const beforeCutoff = isBeforeCutoff(row.Year, row.Month);
        // If before cutoff, show nothing. Else, show number of plays.
        const plays = beforeCutoff ? "" : row.Plays;

        // Store in bool if song was big 16 N1 this month.
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

// This function trims the leading empty months from the monthly data.
function trimLeadingEmptyMonths(data) {
    const firstIndex = data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );

    // If no activity at all, just return original (or empty if you prefer)
    if (firstIndex === -1) return data;

    return data.slice(firstIndex);
}

// This function finds the first active month of a song. Used to filter empty months.
function findFirstActiveIndex(data) {
    return data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );
}

// This function filters empty months AFTER the first month of statistics for the song.
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

// This function is called when the "Hide Empty Months / Show All Months" button is pressed.
// It toggles empty months AFTER the first month of statistics for the song.
function toggleMonths() {
    showAllMonths = !showAllMonths;

    const btn = document.getElementById("toggle-months-btn");
    btn.innerText = showAllMonths ? "Hide Empty Months" : "Show All Months";

    renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));
}

// This function helps find if a month is before last.fm stats tracking or after.
function isBeforeCutoff(year, month) {
    return (
        year < CUTOFF_YEAR ||
        (year === CUTOFF_YEAR && month < CUTOFF_MONTH)
    );
}