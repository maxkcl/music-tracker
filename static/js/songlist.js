let songSort = {
    column: "value",   // default sort = Total Plays
    direction: "desc"
};

let songData = [];

let songFilters = {
    name: "",
    artist: "",
    album: "",
    first_played: { op: ">", val: "" },
    last_played: { op: ">", val: "" },
    value: { op: ">", val: "" }
};

document.addEventListener("DOMContentLoaded", () => {
    renderSongTable(); // build once
    loadSongs();       // fetch + populate
});


function filterSongs(data) {
    return data.filter(item => {
        // text filters
        if (!item.name.toLowerCase().includes(songFilters.name)) return false;
        if (!item.artist.toLowerCase().includes(songFilters.artist)) return false;
        if (!(item.album || "").toLowerCase().includes(songFilters.album)) return false;

        // numeric filter (plays)
        if (songFilters.value.val !== "") {
            const val = parseInt(songFilters.value.val);
            if (!compare(item.value, val, songFilters.value.op)) return false;
        }

        // date filters
        if (songFilters.first_played.val) {
            const itemDate = new Date(item.first_played);
            const filterDate = new Date(songFilters.first_played.val);
            if (!compare(itemDate, filterDate, songFilters.first_played.op)) return false;
        }

        if (songFilters.last_played.val) {
            const itemDate = new Date(item.last_played);
            const filterDate = new Date(songFilters.last_played.val);
            if (!compare(itemDate, filterDate, songFilters.last_played.op)) return false;
        }

        return true;
    });
}

function compare(a, b, op) {
    if (op === ">") return a > b;
    if (op === "<") return a < b;
    if (op === "=") return a == b;
    return true;
}

function createTextFilter(field) {
    const th = document.createElement("th");

    const input = document.createElement("input");
    input.id = "songlistFilter"
    input.placeholder = "Filter...";
    input.value = songFilters[field];

    input.oninput = (e) => {
        songFilters[field] = e.target.value.toLowerCase();
        rerenderSongs();
    };

    th.appendChild(input);
    return th;
}

function createOperatorFilter(field) {
    const th = document.createElement("th");

    const select = document.createElement("select");
    [">", "<", "="].forEach(op => {
        const option = document.createElement("option");
        option.value = op;
        option.textContent = op;
        if (songFilters[field].op === op) option.selected = true;
        select.appendChild(option);
    });

    const input = document.createElement("input");
    input.id = "songlistFilter"
    input.placeholder = "Value";
    input.value = songFilters[field].val;

    select.onchange = () => {
        songFilters[field].op = select.value;
        rerenderSongs();
    };

    input.oninput = (e) => {
        songFilters[field].val = e.target.value;
        rerenderSongs();
    };

    th.appendChild(select);
    th.appendChild(input);
    return th;
}

function sortSongs(data, column, direction) {
    return [...data].sort((a, b) => {
        let valA = a[column] ?? "";
        let valB = b[column] ?? "";

        // numeric
        if (column === "value") {
            return direction === "asc" ? valA - valB : valB - valA;
        }

        // date fields
        if (column === "first_played" || column === "last_played") {
            const dA = new Date(valA);
            const dB = new Date(valB);
            return direction === "asc" ? dA - dB : dB - dA;
        }

        // string
        valA = valA.toString().toLowerCase();
        valB = valB.toString().toLowerCase();

        if (valA < valB) return direction === "asc" ? -1 : 1;
        if (valA > valB) return direction === "asc" ? 1 : -1;
        return 0;
    });
}

function formatDateTime(value) {
    if (!value) return "";

    const d = new Date(value);
    return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric"
    });
}

function createFilterInput(field) {
    const th = document.createElement("th");

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Filter...";
    input.value = songFilters[field];

    input.style.width = "95%";
    input.style.background = "#2c2c3a";
    input.style.color = "#c0d6ff";
    input.style.border = "none";
    input.style.padding = "2px 4px";
    input.style.fontSize = "0.8rem";

    input.oninput = (e) => {
        songFilters[field] = e.target.value.toLowerCase();

        const filtered = filterSongs(songData);
        const sorted = sortSongs(filtered, songSort.column, songSort.direction);

        renderSongTable(sorted);
    };

    th.appendChild(input);
    return th;
}

function rerenderSongs() {
    const filtered = filterSongs(songData);
    const sorted = sortSongs(filtered, songSort.column, songSort.direction);

    // numeric filter
    const op = songFilters.value.op;
    const val = parseInt(songFilters.value.val);

    if (!isNaN(val)) {
        sorted = sorted.filter(song => {
            if (op === ">") return song.value > val;
            if (op === "<") return song.value < val;
            if (op === "=") return song.value === val;
        });
    }

    renderSongRows(sorted);
}

// function rerenderSongs() {
//     const active = document.activeElement;
//     const activeId = active?.id;
//     const cursorPos = active?.selectionStart;

//     const filtered = filterSongs(songData);
//     const sorted = sortSongs(filtered, songSort.column, songSort.direction);
//     renderSongTable(sorted);

//     if (activeId) {
//         const newInput = document.getElementById(activeId);
//         if (newInput) {
//             newInput.focus();
//             if (cursorPos !== null) {
//                 newInput.setSelectionRange(cursorPos, cursorPos);
//             }
//         }
//     }
// }

async function loadSongs() {
    try {
        const startDate = document.getElementById("startDate")?.value;
        const endDate = document.getElementById("endDate")?.value;

        const params = new URLSearchParams();

        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);

        const res = await fetch("/api/songlist?" + params.toString());
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        songData = data;
        rerenderSongs();

    } catch (err) {
        console.error("Fetch failed:", err);
    }
}

function renderSongTable() {
    const columnMap = {
        "Name": "name",
        "Artist": "artist",
        "Album": "album",
        "First Played": "first_played",
        "Last Played": "last_played",
        "Total Plays": "value"
    };
    
    const container = document.getElementById("results");
    container.innerHTML = "";

    const table = document.createElement("table");
    table.classList.add("list-table");

    // ===== HEADER =====
    const thead = document.createElement("thead");

    const trHead = document.createElement("tr");
    ["Rank", "Name", "Artist", "Album", "First Played", "Last Played", "Plays"].forEach(h => {
        const th = document.createElement("th");
        th.textContent = h;
        const key = columnMap[h];

        if (key) {
            th.style.cursor = "pointer";

            if (songSort.column === key) {
                th.textContent += songSort.direction === "asc" ? " ▲" : " ▼";
            }

            th.onclick = () => {
                if (songSort.column === key) {
                    songSort.direction = songSort.direction === "asc" ? "desc" : "asc";
                } else {
                    songSort.column = key;
                    songSort.direction = "desc";
                }

                rerenderSongs();
            };
        }
        trHead.appendChild(th);
    });

    // ===== FILTER ROW =====
    const trFilter = document.createElement("tr");
    trFilter.appendChild(document.createElement("th")); // Rank empty
    trFilter.appendChild(createTextFilter("name"));
    trFilter.appendChild(createTextFilter("artist"));
    trFilter.appendChild(createTextFilter("album"));
    trFilter.appendChild(createOperatorFilter("first_played"));
    trFilter.appendChild(createOperatorFilter("last_played"));
    trFilter.appendChild(createOperatorFilter("value"));

    thead.appendChild(trHead);
    thead.appendChild(trFilter);

    // ===== BODY =====
    const tbody = document.createElement("tbody");
    tbody.id = "songTableBody";

    table.appendChild(thead);
    table.appendChild(tbody);
    container.appendChild(table);

    // initial rows
    renderSongRows(songData);
}

function renderSongRows(data) {
    const tbody = document.getElementById("songTableBody");
    if (!tbody) return;

    tbody.innerHTML = "";

    data.forEach((item, index) => {
        const tr = document.createElement("tr");

        tr.appendChild(tdCell(index + 1));
        tr.appendChild(tdCell(item.name));
        tr.appendChild(tdCell(item.artist));
        tr.appendChild(tdCell(item.album));
        tr.appendChild(tdCell(formatDateTime(item.first_played)));
        tr.appendChild(tdCell(formatDateTime(item.last_played)));
        tr.appendChild(tdCell(item.value));

        tbody.appendChild(tr);
    });
}

// OLD function before fixing select issue
// function renderSongTable(data) {
//     const container = document.getElementById("results");
//     container.innerHTML = "";

//     const table = document.createElement("table");
//     table.classList.add("list-table");

//     const headers = [
//         "Rank",
//         "Song Name",
//         "Artist",
//         "Album",
//         "First Played",
//         "Last Played",
//         "Total Plays"
//     ];

//     const columnMap = {
//         "Song Name": "name",
//         "Artist": "artist",
//         "Album": "album",
//         "First Played": "first_played",
//         "Last Played": "last_played",
//         "Total Plays": "value"
//     };

//     const thead = document.createElement("thead");

//     // HEADER ROW (sorting)
//     const trHead = document.createElement("tr");

//     headers.forEach(h => {
//         const th = document.createElement("th");
//         const key = columnMap[h];

//         th.textContent = h;

//         if (key) {
//             th.style.cursor = "pointer";

//             if (songSort.column === key) {
//                 th.textContent += songSort.direction === "asc" ? " ▲" : " ▼";
//             }

//             th.onclick = () => {
//                 if (songSort.column === key) {
//                     songSort.direction = songSort.direction === "asc" ? "desc" : "asc";
//                 } else {
//                     songSort.column = key;
//                     songSort.direction = "desc";
//                 }

//                 rerenderSongs();
//             };
//         }

//         trHead.appendChild(th);
//     });

//     thead.appendChild(trHead);

//     // FILTER ROW
//     const trFilter = document.createElement("tr");

//     trFilter.appendChild(document.createElement("th")); // rank

//     trFilter.appendChild(createTextFilter("name"));
//     trFilter.appendChild(createTextFilter("artist"));
//     trFilter.appendChild(createTextFilter("album"));

//     trFilter.appendChild(createOperatorFilter("first_played"));
//     trFilter.appendChild(createOperatorFilter("last_played"));
//     trFilter.appendChild(createOperatorFilter("value"));

//     thead.appendChild(trFilter);
//     table.appendChild(thead);

//     // BODY
//     const tbody = document.createElement("tbody");

//     data.forEach((item, index) => {
//         const tr = document.createElement("tr");

//         tr.appendChild(td(index + 1));
//         tr.appendChild(td(item.name));
//         tr.appendChild(td(item.artist));
//         tr.appendChild(td(item.album));
//         tr.appendChild(td(formatDateTime(item.first_played)));
//         tr.appendChild(td(formatDateTime(item.last_played)));
//         tr.appendChild(td(item.value));

//         tbody.appendChild(tr);
//     });

//     table.appendChild(tbody);
//     container.appendChild(table);
// }

function tdCell(content) {
    const cell = document.createElement("td");
    cell.textContent = content ?? "";
    return cell;
}