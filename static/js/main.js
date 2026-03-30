// Table sorting state
let currentSort = {
    column: null,
    direction: "desc" // default
};

let lastData = [];
let lastSelect = null;

// DOM references
const toggleBtn = document.getElementById("toggle-view-btn");
const runQueryBtn = document.getElementById("runQueryBtn");
const listContainer = document.getElementById("results");

// ----------------------------
// Run query
// ----------------------------

async function runQuery() {
    const selectField = document.getElementById("selectField").value;
    const metric = document.getElementById("metric").value;
    const operator = document.getElementById("operator").value;
    const valueInput = document.getElementById("value").value;
    const startDate = document.getElementById("startDate")?.value || null;
    const endDate = document.getElementById("endDate")?.value || null;

    const value = parseInt(valueInput);
    if (isNaN(value)) {
        alert("Please enter a valid number");
        return;
    }

    const payload = { 
        select: selectField, 
        metric, 
        operator, 
        value,
        start_date: startDate || null,
        end_date: endDate || null
    };

    const res = await fetch("/api/query-builder", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.error) {
        alert("Query error: " + data.error);
        return;
    }

    lastData = data;
    lastSelect = selectField;
    
    renderList(data, selectField);
}

function sortData(data, column, direction) {
    return [...data].sort((a, b) => {
        let valA = a[column] ?? "";
        let valB = b[column] ?? "";

        // numeric
        if (column === "value") {
            return direction === "asc" ? valA - valB : valB - valA;
        }

        // date sorting (for day/month/year)
        if (column === "name" && lastSelect && ["day", "month", "year"].includes(lastSelect)) {
            const dateA = new Date(valA);
            const dateB = new Date(valB);
            return direction === "asc" ? dateA - dateB : dateB - dateA;
        }

        // string
        valA = valA.toString().toLowerCase();
        valB = valB.toString().toLowerCase();

        if (valA < valB) return direction === "asc" ? -1 : 1;
        if (valA > valB) return direction === "asc" ? 1 : -1;
        return 0;
    });
}

function formatDate(value, type) {
    if (!value) return "";

    try {
        if (type === "day") {
            // "2026-03-29" → March 29, 2026
            const d = new Date(value);
            return d.toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric"
            });
        }

        if (type === "month") {
            // "2026-03" → March 2026
            const [year, month] = value.split("-");
            const d = new Date(year, month - 1);
            return d.toLocaleDateString("en-US", {
                year: "numeric",
                month: "long"
            });
        }

        if (type === "year") {
            return value.toString();
        }

        return value;
    } catch {
        return value;
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

    headers.forEach((h) => {
        const th = document.createElement("th");

        let columnKey;
        switch (h) {
            case "Name":
            case "Date":
                columnKey = "name";
                break;
            case "Artist":
                columnKey = "artist";
                break;
            case "Album":
                columnKey = "album";
                break;
            case "Plays":
                columnKey = "value";
                break;
            default:
                columnKey = null;
        }

        th.textContent = h;

        if (columnKey) {
            th.style.cursor = "pointer";

            // show sort arrow
            if (currentSort.column === columnKey) {
                th.textContent += currentSort.direction === "asc" ? " ▲" : " ▼";
            }

            th.onclick = () => {
                if (currentSort.column === columnKey) {
                    currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
                } else {
                    currentSort.column = columnKey;
                    currentSort.direction = "desc";
                }

                const sorted = sortData(lastData, columnKey, currentSort.direction);
                renderList(sorted, lastSelect);
            };
        }

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
                tr.appendChild(tdCell(formatDate(item.name, selectType)));
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