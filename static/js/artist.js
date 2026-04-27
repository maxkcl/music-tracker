// ================================================================================================= //
//
//  artist.js
//  - The logic of the individual artist pages.
//
// ================================================================================================= //

let showAllMonths = false;
let fullMonthlyData = [];

// The cutoff is used to distinguish BEFORE and AFTER last.fm scrobbling began.
const CUTOFF_YEAR = 2020;
const CUTOFF_MONTH = 12; // December

// Page load
document.addEventListener("DOMContentLoaded", () => {
    
    // Fetch Artist ID from HTML
    const el = document.querySelector(".artist-page");
    if (!el) {
        console.error("artist-page element not found");
        return;
    }
    const artistId = el.dataset.artistId;

    // Load data
    loadArtist(artistId);
});

// This function loads artist data from the flask route and begins page rendering.
async function loadArtist(artistId) {
    try {
        const res = await fetch(`/api/artist/${artistId}`);
        const data = await res.json();

        // Renders the summary section of the page and the songs table.
        renderArtistSummary(data.summary[0]);
        renderSongs(data.songs);
        
        // Monthly data table. Months before data are trimmed and hidden.
        const trimmed = trimLeadingEmptyMonths(data.monthly);
        fullMonthlyData = trimmed;
        renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));

    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

// This function renders the summary and cards at the top of the page.
function renderArtistSummary(data) {

    const container = document.getElementById("artist-summary");

    const wins = (data.Wins || "").split(";;").filter(Boolean);

    const statCards = [];

    // Big 16 wins card
    if (data.WinCount > 0) {
        statCards.push(`
            <div class="big16-card stat-card">
                <div class="card-title">
                    ${data.WinCount}x Big 16 N1
                </div>
                <div class="card-sub">
                    #${data.WinRank} all-time
                </div>
            </div>
        `);
    }

    // Monthly leader card
    if (data.LeaderCount > 0) {
        statCards.push(`
            <div class="big16-card stat-card">
                <div class="card-title">
                    ${data.LeaderCount}x Month Leader
                </div>
                <div class="card-sub">
                    ${data.BestMonthPlays} in ${formatMonth(data.BestMonthDate)}
                </div>
            </div>
        `);
    }

    const cards = wins.map(w => {
        const [id, name, months] = w.split("|");

        return `
            <div class="big16-card" title="${months}">
                <a href="/song/${id}" class="card-title">${name}</a>
                <div class="card-sub">${months}</div>
            </div>
        `;
    }).join("");

    container.innerHTML = `
        <div class="artist-header">
            
            <div class="artist-left">
                <h1>${data.ArtistName}</h1>

                <div class="stat">Discovered: 
                    ${formatDiscovered(data.FirstPlayed, data.FirstBig16Month)}
                </div>

                <div class="stat">
                    Plays: ${data.TotalPlays} 
                    <span class="rank">(#${data.PlaysRank})</span>
                </div>

                <div class="stat">
                    ${data.TotalPoints == null ? "" : `Big 16 Points: ${data.TotalPoints} 
                    <span class="rank">(#${data.PointsRank})</span>`}
                </div>
            </div>

            <div class="artist-right">
                <div class="card-container stat-row">
                    ${statCards.join("")}
                </div>
                <div class="card-container">
                    ${cards}
                </div>
            </div>

        </div>
    `;
}

// This helper function formats date strings into easily displayed months.
function formatMonth(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("default", {
        month: "short",
        year: "numeric"
    });
}

// This function formats the earliest date of data an artist has.
function formatDiscovered(firstPlayed, firstBig16Month) {
    const cutoff = new Date("2020-12-01");

    if (firstBig16Month) {
        const big16Date = new Date(firstBig16Month);

        if (big16Date < cutoff) {
            return `Before ${big16Date.toLocaleDateString("default", {
                month: "long",
                year: "numeric"
            })}`;
        }
    }

    if (!firstPlayed) return "";

    const d = new Date(firstPlayed);
    return d.toLocaleDateString("default", {
        month: "long",
        day: "numeric",
        year: "numeric"
    });
}

// This function renders the monthly data table.
function renderMonthlyTable(data) {
    
    let html = "<table class='monthly'>";
    
    // HEADER //
    html += `
        <thead>
            <tr>
                <th>Month</th>
                <th>Rank</th>
                <th>Plays</th>
                <th>Top Song</th>
                <th>TPTPs</th>
                <th>In</th>
                <th>Top 16 Songs</th>
            </tr>
        </thead>
        <tbody>
    `;

    // BODY //
    data.forEach(row => {
        const label = new Date(row.Year, row.Month - 1)
            .toLocaleString("default", { month: "short", year: "numeric" });
        
        const beforeCutoff = isBeforeCutoff(row.Year, row.Month);
        const plays = beforeCutoff ? "" : row.Plays;
        // If before cutoff, rank is empty. Else, show rank.
        let rank = beforeCutoff ? "" : "#".concat(row.PlaysRank ?? "");
        // Rank cell should be empty if no plays this month
        if (row.PlaysRank == "") {
            rank = "";
        }

        const isNumberOne = hasNumberOne(row.Top16Songs);
        const isMonthLeader = row.PlaysRank == 1;

        html += `
            <tr>
                <td class="${isNumberOne ? "n1-row" : ""}">${label}</td>
                <td class="${isMonthLeader ? "n1-row" : ""}">${rank}</td>
                <td class="${isMonthLeader ? "n1-row" : ""}">${plays}</td>
                <td>${ row.TopSongID ? makeLink(row.TopSongID, row.TopSong, "song") : "" }</td>
                <td>${row.TopSongPlays ?? ""}</td>
                <td>${row.Top16Count}</td>
                <td class="${isNumberOne ? "n1-row" : ""}">${formatTop16Songs(row.Top16Songs)}</td>
            </tr>
        `;
    });

    html += "</tbody></table>";

    document.getElementById("artist-monthly").innerHTML = html;
}

// This function returns the rows of the monthly data with any leading empty rows removed.
function trimLeadingEmptyMonths(data) {
    const firstIndex = data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );

    // If no activity at all, just return original (or empty if you prefer)
    if (firstIndex === -1) return data;

    return data.slice(firstIndex);
}

// This function takes in the raw top 16 songs data for the monthly table and formats it nicely.
function formatTop16Songs(raw) {
    if (!raw) return "";

    return raw.split(";;").map(item => {
        const [id, name, rank] = item.split("|");

        return `${makeLink(id, name, "song")} (${rank})`;
    }).join(", ");
}

// This function finds the first active month of an artist. Used to filter empty months.
function findFirstActiveIndex(data) {
    return data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );
}

// This function filters empty months AFTER the first month of statistics for the artist.
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
// It toggles empty months AFTER the first month of statistics for the artist.
function toggleMonths() {
    showAllMonths = !showAllMonths;

    const btn = document.getElementById("toggle-months-btn");
    btn.innerText = showAllMonths ? "Hide Empty Months" : "Show All Months";

    renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));
}

// This function finds out if the artist has the number one song of a month.
function hasNumberOne(top16Raw) {
    if (!top16Raw) return false;

    return top16Raw.split(";;").some(item => {
        const parts = item.split("|");
        const rank = Number(parts[2]);
        return rank === 1;
    });
}

// This function helps find if a month is before last.fm stats tracking or after.
function isBeforeCutoff(year, month) {
    return (
        year < CUTOFF_YEAR ||
        (year === CUTOFF_YEAR && month < CUTOFF_MONTH)
    );
}

// This function renders the song table.
function renderSongs(songs) {
    const container = document.getElementById("artist-songs");

    // HEADER //
    let html = "<table>";
    html += "<tr><th>#</th><th style=\"text-align: left;\">Song Name</th><th>OVR</th><th>Plays</th><th>N1s</th><th>B16 Pts</th><th>B16 MIC</th></tr>";

    // BODY //
    let rank = 1;
    songs.forEach(s => {
        // highlightClass will display golden cells if song is top song of any month
        const highlightClass = s.N1s > 0 ? "highlight-n1" : "";
        
        html += `
            <tr>
                <td style="text-align: center;">${rank}</td>
                <td class="${highlightClass}">
                    ${
                        s.ID
                            ? `<a href="/song/${s.ID}" class="song-link">
                                ${s.SongName}
                            </a>`
                            : ""
                    }
                </td>
                <td>${s.Rating ?? ""}</td>
                <td>${s.Plays}</td>
                <td class="${highlightClass}">${s.N1s}</td>
                <td>${s.TP}</td>
                <td>${s.MIC}</td>
            </tr>
        `;
        rank++;
    });

    html += "</table>";

    container.innerHTML = html;
}