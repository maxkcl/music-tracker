let showAllMonths = false;
let fullMonthlyData = [];

const CUTOFF_YEAR = 2020;
const CUTOFF_MONTH = 12; // December

document.addEventListener("DOMContentLoaded", () => {
    const el = document.querySelector(".artist-page");

    if (!el) {
        console.error("artist-page element not found");
        return;
    }

    const artistId = el.dataset.artistId;

    console.log("Artist ID:", artistId);
    loadArtist(artistId);
});

async function loadArtist(artistId) {
    try {
        const res = await fetch(`/api/artist/${artistId}`);
        const data = await res.json();

        renderSongs(data.songs);
        renderArtistSummary(data.summary[0]);

        const trimmed = trimLeadingEmptyMonths(data.monthly);
        fullMonthlyData = trimmed;
        renderMonthlyTable(filterMonths(fullMonthlyData, showAllMonths));
        

    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

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

function formatMonth(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("default", {
        month: "short",
        year: "numeric"
    });
}

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

function renderMonthlyTable(data) {
    
    let html = "<table class='monthly'>";
    
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

    data.forEach(row => {
        const label = new Date(row.Year, row.Month - 1)
            .toLocaleString("default", { month: "short", year: "numeric" });
        
        const beforeCutoff = isBeforeCutoff(row.Year, row.Month);
        const plays = beforeCutoff ? "" : row.Plays;
        let rank = beforeCutoff ? "" : "#".concat(row.PlaysRank ?? "");
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

function trimLeadingEmptyMonths(data) {
    const firstIndex = data.findIndex(row =>
        (row.Plays && row.Plays > 0) ||
        (row.Top16Count && row.Top16Count > 0)
    );

    // If no activity at all, just return original (or empty if you prefer)
    if (firstIndex === -1) return data;

    return data.slice(firstIndex);
}

function formatTop16Songs(raw) {
    if (!raw) return "";

    return raw.split(";;").map(item => {
        const [id, name, rank] = item.split("|");

        return `${makeLink(id, name, "song")} (${rank})`;
    }).join(", ");
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

function hasNumberOne(top16Raw) {
    if (!top16Raw) return false;

    return top16Raw.split(";;").some(item => {
        const parts = item.split("|");
        const rank = Number(parts[2]);
        return rank === 1;
    });
}

function isBeforeCutoff(year, month) {
    return (
        year < CUTOFF_YEAR ||
        (year === CUTOFF_YEAR && month < CUTOFF_MONTH)
    );
}

function renderSongs(songs) {
    const container = document.getElementById("artist-songs");

    let html = "<table>";
    html += "<tr><th>#</th><th style=\"text-align: left;\">Song Name</th><th>OVR</th><th>Plays</th><th>N1s</th><th>B16 Pts</th><th>B16 MIC</th></tr>";

    let i = 1;
    songs.forEach(s => {
        const highlightClass = s.N1s > 0 ? "highlight-n1" : "";
        
        html += `
            <tr>
                <td style="text-align: center;">${i}</td>
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
        i++;
    });

    html += "</table>";

    container.innerHTML = html;
}