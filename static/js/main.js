let chartInstance = null;
let lastData = [];

async function runQuery() {
    const payload = {
        select: document.getElementById("selectField").value,
        metric: document.getElementById("metric").value,
        operator: document.getElementById("operator").value,
        value: parseInt(document.getElementById("value").value)
    };

    const res = await fetch("/api/query-builder", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    renderCards(data);
}

function renderCards(data) {
    const container = document.getElementById("resultsContainer");
    container.innerHTML = "";

    if (!data.length) {
        container.innerHTML = "<p>No results</p>";
        return;
    }

    data.forEach((row, index) => {
        const img = row.ImageURL || "https://via.placeholder.com/300x300?text=No+Image";

        const card = `
            <div class="card">
                <img src="${img}">
                <div class="card-title">${row.label}</div>
                <div class="card-value">${row.value} plays</div>
                <div>#${index + 1}</div>
            </div>
        `;

        container.innerHTML += card;
    });
}

function renderCell(row, column) {
    // Normalize column name
    const col = column.toLowerCase();

    // Artist
    if (col.includes("artist") && row.ImageURL) {
        return `
            <div style="display:flex;align-items:center;gap:8px;">
                <img src="${row.ImageURL}" width="40" height="40" style="border-radius:50%;">
                ${row[column]}
            </div>
        `;
    }

    // Album
    if (col.includes("album") && row.ImageURL) {
        return `
            <div style="display:flex;align-items:center;gap:8px;">
                <img src="${row.ImageURL}" width="40" height="40">
                ${row[column]}
            </div>
        `;
    }

    // Song → use album art
    if (col.includes("song") && row.ImageURL) {
        return `
            <div style="display:flex;align-items:center;gap:8px;">
                <img src="${row.ImageURL}" width="40" height="40">
                ${row[column]}
            </div>
        `;
    }

    return row[column];
}

let currentView = "card";

function toggleView() {
    const container = document.getElementById("resultsContainer");

    if (currentView === "card") {
        container.classList.remove("card-view");
        container.classList.add("grid-view");
        currentView = "grid";
    } else {
        container.classList.remove("grid-view");
        container.classList.add("card-view");
        currentView = "card";
    }
}