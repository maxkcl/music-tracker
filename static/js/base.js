// ================================================================================================= //
//
//  base.js
//  - The logic shared across all pages, such as the banner.
//
// ================================================================================================= //

let nowPlayingInterval = null;

// If page is visible, fetch for now playing results.
// If page is not visible, stop fetching.
document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        stopNowPlayingPolling();
    } else {
        startNowPlayingPolling();
    }
});

// This function tells the page to start fetching now playing data.
function startNowPlayingPolling() {
    if (nowPlayingInterval) return;
    updateNowPlaying();
    nowPlayingInterval = setInterval(updateNowPlaying, 5000);
}

// This function tells the page to stop fetching now playing data.
function stopNowPlayingPolling() {
    if (nowPlayingInterval) {
        clearInterval(nowPlayingInterval);
        nowPlayingInterval = null;
    }
}

// This function fetches data from last.fm to find if the user is currently
// listening to anything, and displays on the banner.
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

// This helper function takes in an ID, Name, and Type (song, artist, etc.) and creates a link connecting
// the displayed name to the matching page.
function makeLink(id, text, type) {
    if (!id || id == 0) return text;
    return `<a href="/${type}/${id}" class="${type}-link">${text}</a>`;
}

updateNowPlaying(); // initial load