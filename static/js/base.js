async function updateNowPlaying() {
    try {
        const res = await fetch("/api/now-playing");
        const data = await res.json();

        const banner = document.getElementById("now-playing-banner");

        if (!banner) return;

        if (data.playing) {
            banner.classList.remove("hidden");
            banner.textContent = `Now Playing: ${data.artist} — ${data.song}`;
        } else {
            banner.classList.add("hidden");
        }

    } catch (err) {
        console.error("Now playing fetch failed:", err);
    }
}

setInterval(updateNowPlaying, 5000); // every 5 sec
updateNowPlaying(); // initial load