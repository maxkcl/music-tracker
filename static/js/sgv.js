document.addEventListener("DOMContentLoaded", () => {
    loadRatings();       // fetch + populate
});

async function loadRatings() {
    try {
        const res = await fetch("/api/sgv-get-ratings");
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }
        
        renderSongTable(data);

    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

function renderSongTable(data) {
    const container = document.getElementById("sgv-table");

    let html = `
    <table class="sgv">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Song</th>
                <th>Artist</th>
                <th>Rating</th>
                <th>Points</th>
                <th>First Places</th>
                <th>Appearances</th>
                <th>Scrobbles</th>
                <th>Decayed</th>
            </tr>
        </thead>
        <tbody>
    `;

    let i = 1;
    data.forEach(row => {
        html += `
        <tr>
            <td>${i}</td>
            <td>${makeLink(row.SongID, row.SongName, "song")}</td>
            <td>${makeLink(row.ArtistID, row.ArtistName, "artist")}</td>
            <td>
                <strong>${row.Rating}</strong>
                <span class="rating-arrow">
                    ${getArrow(row.RatingDiff)} ${Math.abs(row.RatingDiff) == 0 ? "": Math.abs(row.RatingDiff)}
                </span>
            </td>
            <td>${row.TP}</td>
            <td>${row.N1s}</td>
            <td>${row.MIC}</td>
            <td>${row.Plays}</td>
            <td>${Math.round(row.DecayedPlays)}</td>
        </tr>
        `;
        i++;
    });

    html += "</tbody></table>";

    container.innerHTML = html;
}

function getArrow(diff) {
    if (diff > 0) return `<span class="rating-arrow rating-up">↑</span>`;
    if (diff < 0) return `<span class="rating-arrow rating-down">↓</span>`;
    return `<span class="rating-arrow rating-same"></span>`;
}