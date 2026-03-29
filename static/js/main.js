// DOM references
const toggleBtn = document.getElementById("toggle-view-btn");
const runQueryBtn = document.getElementById("runQueryBtn");
const listContainer = document.getElementById("results");

// ----------------------------
// Run query
// ----------------------------
runQueryBtn.addEventListener("click", runQuery);

async function runQuery() {
    const selectField = document.getElementById("selectField").value;
    const metric = document.getElementById("metric").value;
    const operator = document.getElementById("operator").value;
    const valueInput = document.getElementById("value").value;

    const value = parseInt(valueInput);
    if (isNaN(value)) {
        alert("Please enter a valid number for the value field");
        return;
    }

    const payload = { select: selectField, metric, operator, value };

    try {
        const res = await fetch("/api/query-builder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const text = await res.text();
            console.error("Server error:", text);
            alert("Query failed. Check console for details.");
            return;
        }

        const data = await res.json();
        renderList(data, selectField);  // ONLY renderList now
    } catch (err) {
        console.error("Fetch error:", err);
        alert("Failed to fetch results. Check console for details.");
    }
}

function renderList(data, selectType) {
    const container = document.getElementById("results");
    if (!container) return;

    container.innerHTML = "";

    if (!data || data.length === 0) {
        container.innerHTML = "<p>No results found.</p>";
        return;
    }

    // Headers
    let headers = ["Rank"];
    switch (selectType) {
        case "song":
            headers.push("Name", "Artist", "Album", "Plays");
            break;
        case "album":
            headers.push("Name", "Artist", "Plays");
            break;
        case "artist":
            headers.push("Name", "Plays");
            break;
        case "day":
        case "month":
        case "year":
            headers.push("Date", "Plays");
            break;
    }

    const table = document.createElement("table");
    table.classList.add("list-table");

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    headers.forEach(h => {
        const th = document.createElement("th");
        th.textContent = h;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    data.forEach((item, index) => {
        const tr = document.createElement("tr");
        tr.appendChild(tdCell(index + 1));

        switch (selectType) {
            case "song":
                tr.appendChild(tdCell(item.name));
                tr.appendChild(tdCell(item.artist));
                tr.appendChild(tdCell(item.album));
                tr.appendChild(tdCell(item.value));
                break;
            case "album":
                tr.appendChild(tdCell(item.name));
                tr.appendChild(tdCell(item.artist));
                tr.appendChild(tdCell(item.value));
                break;
            case "artist":
                tr.appendChild(tdCell(item.name));
                tr.appendChild(tdCell(item.value));
                break;
            case "day":
            case "month":
            case "year":
                tr.appendChild(tdCell(item.name));
                tr.appendChild(tdCell(item.value));
                break;
        }

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}

function tdCell(content) {
    const td = document.createElement("td");
    td.textContent = content ?? "";
    return td;
}