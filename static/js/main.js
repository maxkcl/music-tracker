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
    renderTable(data);
}

function renderTable(data) {
    const table = document.getElementById("resultsTable");
    table.innerHTML = "";

    if (!data.length) {
        table.innerHTML = "<tr><td>No results</td></tr>";
        return;
    }

    const headers = Object.keys(data[0]);

    let headerRow = "<tr>";
    headers.forEach(h => headerRow += `<th onclick="sortTable('${h}')">${h}</th>`);
    headerRow += "</tr>";

    table.innerHTML += headerRow;

    data.forEach(row => {
        let tr = "<tr>";
        headers.forEach(h => tr += `<td>${row[h]}</td>`);
        tr += "</tr>";
        table.innerHTML += tr;
    });
}

function sortTable(column) {
    lastData.sort((a, b) => (b[column] > a[column] ? 1 : -1));
    renderTable(lastData);
}

function toggleChart() {
    if (!lastData.length) return;

    const ctx = document.getElementById("chart");

    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
        return;
    }

    chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: lastData.map(d => d.label),
            datasets: [{
                label: "Plays",
                data: lastData.map(d => d.plays)
            }]
        }
    });
}