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
    const res = await fetch(`/api/artist/${artistId}`);
    const data = await res.json();

    document.getElementById("artist-name").innerText = data.name;

    renderSummary(data);
    renderSongs(data.songs);
}

function renderSummary(data) {

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
                <td class="${highlightClass}">${s.SongName}</td>
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

loadArtist();