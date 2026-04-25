let nowPlayingInterval = null;

document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        stopNowPlayingPolling();
    } else {
        startNowPlayingPolling();
    }
});

function startNowPlayingPolling() {
    if (nowPlayingInterval) return;
    updateNowPlaying();
    nowPlayingInterval = setInterval(updateNowPlaying, 5000);
}

function stopNowPlayingPolling() {
    if (nowPlayingInterval) {
        clearInterval(nowPlayingInterval);
        nowPlayingInterval = null;
    }
}

async function updateNowPlaying() {
    try {
        const res = await fetch("/api/now-playing");
        const data = await res.json();

        const banner = document.getElementById("now-playing-banner");

        if (!banner) return;

        if (data.playing) {
            banner.classList.remove("hidden");
            banner.innerHTML = `
                Now Playing: 
                ${makeLink(data.artist_id, data.artist, "artist")}
                — 
                ${makeLink(data.song_id, data.song, "song")}
            `;
        } else {
            banner.classList.add("hidden");
        }

    } catch (err) {
        console.error("Now playing fetch failed:", err);
    }
}

function makeLink(id, text, type) {
    if (!id || id == 0) return text;
    return `<a href="/${type}/${id}" class="${type}-link">${text}</a>`;
}

updateNowPlaying(); // initial load