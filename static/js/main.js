// Store last data for optional re-render
let lastData = [];

// Run the query when user submits
async function runQuery() {
    // Build payload from input fields
    const selectField = document.getElementById("selectField").value;
    const metric = document.getElementById("metric").value;
    const operator = document.getElementById("operator").value;
    const valueInput = document.getElementById("value").value;

    // Validate numeric input
    const value = parseInt(valueInput);
    if (isNaN(value)) {
        alert("Please enter a valid number for the value field");
        return;
    }

    const payload = {
        select: selectField,
        metric: metric,
        operator: operator,
        value: value
    };

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
        lastData = data; // store for potential re-rendering

        // Unified render function handles both List/Grid views
        renderResults(data);

        // Optional: alert if no results
        if (!data || data.length === 0) {
            alert("No results found for this query");
        }
    } catch (err) {
        console.error("Fetch error:", err);
        alert("Failed to fetch results. Check console for details.");
    }
}

// Optionally, you can allow re-rendering last results after changing view
function refreshView() {
    if (lastData && lastData.length > 0) {
        renderResults(lastData);
    }
}

// Tie refreshView to your toggle button if you want smooth switching without re-fetching
const toggleBtn = document.getElementById("toggle-view-btn");
toggleBtn.addEventListener("click", refreshView);

// Toggle button logic
const gridContainer = document.getElementById("results-grid");
const listContainer = document.getElementById("results-list");

let isGrid = false; // start in list view

toggleBtn.addEventListener("click", () => {
    if (isGrid) {
        gridContainer.style.display = "none";
        listContainer.style.display = "block";
        toggleBtn.textContent = "Switch to Grid View";
    } else {
        gridContainer.style.display = "grid";
        listContainer.style.display = "none";
        toggleBtn.textContent = "Switch to List View";
    }
    isGrid = !isGrid;
});

// Render wrapper
function renderResults(data) {
    if (!data || !Array.isArray(data)) return;

    renderGrid(data);
    renderList(data);
}

// Grid renderer
function renderGrid(data) {
    const container = document.getElementById("results-grid");
    container.innerHTML = "";

    data.forEach((row, index) => {
        const card = document.createElement("div");
        card.className = "card";

        // Rank
        const rank = document.createElement("div");
        rank.className = "rank";
        rank.textContent = `#${index + 1}`;
        card.appendChild(rank);

        // Name
        const name = document.createElement("div");
        name.className = "name";
        name.textContent = row.name;
        card.appendChild(name);

        // Details (Artist / Album for songs)
        if (row.artist || row.album) {
            const details = document.createElement("div");
            details.className = "details";

            let detailText = "";
            if (row.artist) detailText += `Artist: ${row.artist} `;
            if (row.album) detailText += `Album: ${row.album}`;

            details.textContent = detailText;
            card.appendChild(details);
        }

        // Value
        const value = document.createElement("div");
        value.className = "value";
        value.textContent = row.value;
        card.appendChild(value);

        container.appendChild(card);
    });
}

// List renderer
function renderList(data) {
    const tbody = document.querySelector("#results-table tbody");
    tbody.innerHTML = "";

    data.forEach((row, index) => {
        const tr = document.createElement("tr");

        const rankTd = document.createElement("td");
        rankTd.className = "rank-col";
        rankTd.textContent = index + 1;

        const nameTd = document.createElement("td");
        nameTd.textContent = row.name;

        const detailsTd = document.createElement("td");
        let detailText = "";
        if (row.artist) detailText += `Artist: ${row.artist} `;
        if (row.album) detailText += `Album: ${row.album}`;
        detailsTd.textContent = detailText;

        const valueTd = document.createElement("td");
        valueTd.textContent = row.value;

        tr.appendChild(rankTd);
        tr.appendChild(nameTd);
        tr.appendChild(detailsTd);
        tr.appendChild(valueTd);

        tbody.appendChild(tr);
    });
}