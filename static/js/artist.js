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

        document.getElementById("artist-name").innerText = data.name;

        renderSongs(data.songs);

        const res1 = await fetch(`/api/artist/${artistId}/monthly`);

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
        const rank = beforeCutoff ? "" : "#".concat(row.PlaysRank ?? "");

        const isNumberOne = hasNumberOne(row.Top16Songs);

        html += `
            <tr>
                <td class="${isNumberOne ? "n1-row" : ""}">${label}</td>
                <td>${rank}</td>
                <td>${plays}</td>
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