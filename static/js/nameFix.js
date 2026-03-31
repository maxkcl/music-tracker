document.addEventListener("DOMContentLoaded", () => {

    const artistInput = document.getElementById("artist-input");
    const artistDropdown = document.getElementById("artist-dropdown");
    const songSelect = document.getElementById("song-select");
    const applyBtn = document.getElementById("apply-fix-btn");

    // Sync button
    const syncBtn = document.getElementById("sync-btn");

    let artists = [];

    // 🔹 Load all artists once
    fetch("/artists")
        .then(res => res.json())
        .then(data => {
            artists = data;
            console.log("✅ Artists loaded:", artists.length);
        })
        .catch(err => {
            console.error("❌ Failed to load artists:", err);
        });

    // 🔹 Clear selected artist ID when typing
    artistInput.addEventListener("input", () => {
        artistInput.dataset.id = "";
        const query = artistInput.value.toLowerCase();

        artistDropdown.innerHTML = "";

        if (!query) return;

        const matches = artists.filter(a =>
            a.name.toLowerCase().includes(query)
        );

        matches.slice(0, 20).forEach(a => {
            const div = document.createElement("div");
            div.textContent = a.name;

            div.onclick = () => {
                artistInput.value = a.name;
                artistInput.dataset.id = a.id;  // ✅ store ID
                artistDropdown.innerHTML = "";

                loadSongs(a.id);
            };

            artistDropdown.appendChild(div);
        });
    });

    // 🔹 Load songs for selected artist
    function loadSongs(artistId) {
        songSelect.innerHTML = `<option value="">-- Select Song --</option>`;

        fetch(`/songs?artist_id=${artistId}`)
            .then(res => res.json())
            .then(data => {
                console.log("🎵 Songs loaded:", data.length);

                data.forEach(song => {
                    const opt = document.createElement("option");
                    opt.value = song;
                    opt.textContent = song;
                    songSelect.appendChild(opt);
                });
            })
            .catch(err => {
                console.error("❌ Failed to load songs:", err);
            });
    }

    // 🔹 Apply fix button
    applyBtn.addEventListener("click", async () => {
        const artistId = artistInput.dataset.id;
        const artistName = artistInput.value.trim();
        const song = songSelect.value;
        const newName = document.getElementById("new-name").value.trim();

        // 🚨 Validation
        if (!artistId) {
            showPopup("❌ Please select an artist from the dropdown");
            return;
        }

        if (!newName) {
            showPopup("❌ Please enter a new name");
            return;
        }

        try {
            const res = await fetch("/apply_fix", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    artist_id: artistId,
                    song: song,
                    new_name: newName
                })
            });

            const data = await res.json();

            if (data.status === "ok") {
                showPopup("✅ Fix applied successfully");

                // Optional: clear inputs
                artistInput.value = "";
                artistInput.dataset.id = "";
                songSelect.innerHTML = `<option value="">-- Select Song --</option>`;
                document.getElementById("new-name").value = "";

            } else {
                showPopup("❌ " + (data.message || "Failed to apply fix"));
            }

        } catch (err) {
            console.error(err);
            showPopup("❌ Request failed");
        }
    });

    syncBtn.addEventListener("click", async () => {
        const response = await fetch("/run-fetch", { method: "POST" });
        const data = await response.json();
        if (data.success) {
            showPopup("✅ Yeah buddy your scrobs are in")
        } else {
            console.log(data.error);
            showPopup("❌ Sync failed");
        }
    });
});


// 🔹 Popup helpers
function showPopup(message) {
    document.getElementById("popup-message").textContent = message;
    document.getElementById("popup").classList.remove("hidden");
}

function closePopup() {
    document.getElementById("popup").classList.add("hidden");
}



// DUPLICATE SONG FINDER
let duplicateGroups = [];
let currentIndex = 0;
let selectedSongId = null;

async function openDuplicateViewer() {
    const res = await fetch("/api/song-duplicates");
    duplicateGroups = await res.json();

    currentIndex = 0;

    if (!duplicateGroups.length) {
        alert("No duplicates found");
        return;
    }

    document.getElementById("duplicate-modal").classList.remove("hidden");
    loadDuplicate();
}

async function loadDuplicate() {
    const group = duplicateGroups[currentIndex];

    document.getElementById("duplicate-title").textContent =
        `${group.SongName} — ${group.ArtistName} (${currentIndex + 1}/${duplicateGroups.length})`;

    const res = await fetch(`/api/song-duplicates/details?song=${encodeURIComponent(group.SongName)}&artist_fk=${group.Artist_FK}`);
    const songs = await res.json();

    renderDuplicateDetails(songs);
}

function renderDuplicateDetails(songs) {
    const container = document.getElementById("duplicate-list");
    container.innerHTML = "";

    selectedSongId = null; // reset selection each time

    songs.forEach(s => {
        const div = document.createElement("div");
        div.classList.add("duplicate-row");

        div.textContent = `ID: ${s.ID} | Album: ${s.AlbumName || "None"} | Plays: ${s.plays}`;

        div.onclick = () => {
            // remove previous selection
            document.querySelectorAll(".duplicate-row").forEach(el => {
                el.classList.remove("selected");
            });

            // select this one
            div.classList.add("selected");
            selectedSongId = s.ID;
        };

        container.appendChild(div);
    });

    if (songs.length > 0) {
        selectedSongId = songs[0].ID;
    }
    container.firstChild?.classList.add("selected");
}

function nextDuplicate() {
    if (currentIndex < duplicateGroups.length - 1) {
        currentIndex++;
        loadDuplicate();
    }
}

function prevDuplicate() {
    if (currentIndex > 0) {
        currentIndex--;
        loadDuplicate();
    }
}

function closeDuplicateViewer() {
    document.getElementById("duplicate-modal").classList.add("hidden");
}