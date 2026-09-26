let riskChart = null;
let currentCompanyId = null;
let graphRequest = 0;
let graphFrame = null;
let riskBands = window.riskBands;
let batchResults = [];

document.getElementById("refreshGraphButton").addEventListener("click", loadCompanyGraph);

async function loadCompanyGraph() {
    const requestId = ++graphRequest;
    cancelAnimationFrame(graphFrame);
    document.getElementById("companyGraph").classList.add("hidden");
    document.getElementById("graphDetails").textContent = "";
    const status = document.getElementById("graphStatus");
    status.textContent = "Загрузка связей...";
    try {
        const response = await fetch("/api/graph", { cache: "no-store" });
        const graph = await response.json();
        if (requestId !== graphRequest) return;
        if (!response.ok) {
            status.textContent = graph.error || "Не удалось загрузить граф связей.";
            return;
        }
        renderCompanyGraph(graph);
    } catch (error) {
        if (requestId === graphRequest) status.textContent = "Не удалось загрузить граф связей. Нажмите «Обновить».";
    }
}

function renderCompanyGraph(graph) {
    riskBands = graph.risk_bands || riskBands;
    cancelAnimationFrame(graphFrame);
    const svg = document.getElementById("companyGraph");
    const status = document.getElementById("graphStatus");
    const details = document.getElementById("graphDetails");
    svg.replaceChildren();
    details.textContent = "";
    const linkedIds = new Set(graph.edges.flatMap(edge => [edge.source, edge.target]));
    const nodes = graph.nodes.filter(node => linkedIds.has(node.id)).map((node, i, all) => ({
        ...node, x: 450 + 180 * Math.cos(2 * Math.PI * i / all.length),
        y: 230 + 150 * Math.sin(2 * Math.PI * i / all.length), vx: 0, vy: 0,
    }));
    svg.classList.toggle("hidden", nodes.length < 2);
    if (nodes.length < 2) {
        status.textContent = "Связанные профили пока не найдены";
        return;
    }
    status.textContent = `Связанных профилей: ${nodes.length}. Нажмите на узел для просмотра.`;
    const byId = new Map(nodes.map(node => [node.id, node]));
    function element(tag, attributes, parent = svg) {
        const item = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, value));
        parent.appendChild(item);
        return item;
    }
    const edges = graph.edges.filter(edge => byId.has(edge.source) && byId.has(edge.target)).map(edge => {
        const phone = edge.reason === "same phone";
        const line = element("path", { fill: "none", stroke: phone ? "#788985" : "#320A6B",
            "stroke-width": 2, "stroke-dasharray": phone ? "none" : "6 4" });
        element("title", {}, line).textContent = phone ? "Одинаковый телефон" : "Одинаковое значение соцсетей";
        return { ...edge, line, source: byId.get(edge.source), target: byId.get(edge.target) };
    });
    nodes.forEach(node => {
        const name = node.name || "Название не указано";
        const score = node.risk_score;
        const known = typeof score === "number" && Number.isFinite(score);
        const description = `${name}. Оценка риска: ${known ? `${score}/100` : "не указана"}`;
        node.element = element("g", { role: "button", tabindex: 0, "aria-label": description });
        element("circle", { r: 18, fill: !known ? "#788985" : score < riskBands.medium ? "#0f828c"
            : score < riskBands.high ? "#065084" : "#320A6B" }, node.element);
        element("title", {}, node.element).textContent = description;
        element("text", { y: 34, "text-anchor": "middle", fill: "#162d35", "font-size": 12 }, node.element)
            .textContent = name.length > 22 ? name.slice(0, 21) + "…" : name;
        const select = () => { details.textContent = description; };
        node.element.addEventListener("click", select);
        node.element.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); }
        });
    });
    let iteration = 0;
    function step() {
        nodes.forEach(node => { node.vx += (450 - node.x) * 0.001; node.vy += (230 - node.y) * 0.001; });
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const a = nodes[i], b = nodes[j];
                const dx = a.x - b.x || 0.1, dy = a.y - b.y || 0.1;
                const force = 650 / Math.max(dx * dx + dy * dy, 100);
                a.vx += dx * force; a.vy += dy * force;
                b.vx -= dx * force; b.vy -= dy * force;
            }
        }
        edges.forEach(({ source: a, target: b }) => {
            const dx = b.x - a.x, dy = b.y - a.y;
            const distance = Math.max(1, Math.hypot(dx, dy));
            const force = (distance - 150) * 0.003 / distance;
            a.vx += dx * force; a.vy += dy * force;
            b.vx -= dx * force; b.vy -= dy * force;
        });
        nodes.forEach(node => {
            node.vx *= 0.7; node.vy *= 0.7;
            node.x = Math.max(85, Math.min(815, node.x + Math.max(-8, Math.min(8, node.vx))));
            node.y = Math.max(30, Math.min(410, node.y + Math.max(-8, Math.min(8, node.vy))));
            node.element.setAttribute("transform", `translate(${node.x},${node.y})`);
        });
        edges.forEach(({ source: a, target: b, reason, line }) => {
            const offset = reason === "same phone" ? 12 : -12;
            line.setAttribute("d", `M ${a.x} ${a.y} Q ${(a.x + b.x) / 2 + offset} ${(a.y + b.y) / 2 + offset} ${b.x} ${b.y}`);
        });
        if (++iteration < 180) {
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) step();
            else graphFrame = requestAnimationFrame(step);
        }
    }
    step();
}

loadCompanyGraph();
let regionsChart = null;
let regionsRequest = 0;

document.getElementById("refreshRegionsButton").addEventListener("click", loadRegionsSummary);

async function loadRegionsSummary() {
    const requestId = ++regionsRequest;
    const status = document.getElementById("regionsStatus");
    const container = document.getElementById("regionsChartContainer");
    status.textContent = "Загрузка сводки...";
    container.classList.add("hidden");
    try {
        const response = await fetch("/api/regions/summary", { cache: "no-store" });
        const result = await response.json();
        if (requestId !== regionsRequest) return;
        if (!response.ok || !result.success) {
            status.textContent = result.error || "Не удалось загрузить сводку по регионам.";
            return;
        }
        riskBands = result.risk_bands || riskBands;
        renderRegionsChart(result.regions);
    } catch (error) {
        if (requestId === regionsRequest) {
            status.textContent = "Не удалось показать сводку по регионам. Проверьте соединение и нажмите «Обновить».";
        }
    }
}

function renderRegionsChart(regions) {
    const status = document.getElementById("regionsStatus");
    const container = document.getElementById("regionsChartContainer");
    if (regionsChart) {
        regionsChart.destroy();
        regionsChart = null;
    }
    container.classList.toggle("hidden", regions.length === 0);
    if (!regions.length) {
        status.textContent = "Сохранённых записей пока нет.";
        return;
    }
    status.textContent = "Количество компаний указано рядом с регионом. Подробности — при наведении. Для регионов без оценок полоса не отображается.";
    container.style.height = `${Math.max(240, regions.length * 52 + 70)}px`;
    regionsChart = new Chart(document.getElementById("regionsChart"), {
        type: "bar",
        data: {
            labels: regions.map(item => `${item.region} — компаний: ${item.company_count}${item.average_risk_score === null ? " (нет оценок)" : ""}`),
            datasets: [{
                label: "Средняя оценка риска",
                data: regions.map(item => item.average_risk_score),
                backgroundColor: regions.map(item => item.average_risk_score === null ? "#788985"
                    : item.average_risk_score < riskBands.medium ? "#0f828c"
                    : item.average_risk_score < riskBands.high ? "#065084" : "#320A6B"),
                borderRadius: 5,
            }],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    min: 0, max: 100,
                    title: { display: true, text: "Средняя оценка риска, баллы", color: "#344e56" },
                    ticks: { color: "#344e56" },
                },
                y: { ticks: { color: "#344e56", autoSkip: false } },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: context => {
                            const item = regions[context.dataIndex];
                            return [
                                `Средняя оценка: ${item.average_risk_score.toLocaleString("ru-RU")}/100`,
                                `Компаний: ${item.company_count}`,
                                `С высоким риском: ${item.high_risk_count}`,
                            ];
                        },
                    },
                },
            },
        },
    });
}

loadRegionsSummary();

document.getElementById("downloadReportButton").addEventListener("click", downloadReport);

async function downloadReport() {
    const companyId = currentCompanyId;
    if (!Number.isInteger(companyId) || companyId <= 0) return;
    const format = document.getElementById("reportFormat").value;
    const button = document.getElementById("downloadReportButton");
    const status = document.getElementById("downloadReportStatus");
    button.disabled = true;
    status.textContent = "Подготовка отчёта...";
    try {
        const response = await fetch(`/api/report/${companyId}/download?format=${encodeURIComponent(format)}`);
        if (!response.ok) {
            const error = await response.json();
            status.textContent = error.error || "Не удалось скачать отчёт.";
            return;
        }
        const url = URL.createObjectURL(await response.blob());
        const link = document.createElement("a");
        link.href = url;
        link.download = `otchet_${companyId}.${format}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        status.textContent = "Файл передан браузеру для скачивания.";
    } catch (error) {
        status.textContent = "Не удалось скачать отчёт. Проверьте соединение и повторите попытку.";
    } finally {
        button.disabled = false;
    }
}

document.getElementById("manualEntryForm").addEventListener("submit", submitManualEntry);

async function submitManualEntry(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = document.getElementById("manualEntryButton");
    const status = document.getElementById("manualEntryStatus");
    button.disabled = true;
    status.textContent = "Сохранение и анализ данных...";
    try {
        const response = await fetch("/api/manual-entry", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.fromEntries(new FormData(form)))
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            status.textContent = result.error || "Не удалось сохранить компанию.";
            return;
        }
        document.getElementById("batchResults").classList.add("hidden");
        renderDashboard(result.analysis, result.ai_report, result.company?.id);
        status.textContent = `Компания «${result.company.name}» сохранена. Номер записи: ${result.company.id}.`;
    } catch (error) {
        status.textContent = "Не удалось получить результат. Проверьте соединение. Запись могла сохраниться — повторная отправка создаст новую запись.";
    } finally {
        button.disabled = false;
    }
}

async function analyzeData() {
    const input = document.getElementById("fileInput");
    const button = document.getElementById("analyzeButton");
    const loading = document.getElementById("loading");

    if (!input.files.length) {
        alert("Выберите CSV или Excel файл.");
        return;
    }

    const form = new FormData();
    form.append("file", input.files[0]);

    button.disabled = true;
    loading.classList.remove("hidden");

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            body: form
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.error || "Ошибка анализа");
        }

        batchResults = result.results;
        const quality = result.dataset_analysis;
        document.getElementById("batchResults").classList.remove("hidden");
        document.getElementById("datasetQuality").textContent = `Строк: ${quality.rows}; пропусков: ${quality.missing_values}; дубликатов: ${quality.duplicates}. Эти показатели не влияют на риск компаний.`;
        const diagnostics = document.getElementById("datasetAnomalies");
        diagnostics.replaceChildren();
        for (const signal of quality.anomalies) {
            const li = document.createElement("li");
            li.textContent = `${signal.column}: ${signal.count} (${signal.threshold})`;
            diagnostics.appendChild(li);
        }
        if (!quality.anomalies.length) diagnostics.textContent = "Отклонений ±3σ не найдено.";
        const select = document.getElementById("companyResultSelect");
        select.replaceChildren();
        batchResults.forEach((item, index) => {
            const option = document.createElement("option");
            option.value = index;
            option.textContent = `Строка ${item.row}: ${item.company.name || "Без названия"} — ${item.analysis.risk_score}/100`;
            select.appendChild(option);
        });
        showBatchCompany();

    } catch (error) {
        alert(error.message);
    } finally {
        button.disabled = false;
        loading.classList.add("hidden");
    }
}

document.getElementById("companyResultSelect").addEventListener("change", showBatchCompany);
function showBatchCompany() {
    const item = batchResults[Number(document.getElementById("companyResultSelect").value)];
    if (item) renderDashboard(item.analysis, item.ai_report, item.company.id);
}

function renderDashboard(data, report, companyId = null) {
    loadCompanyGraph();
    loadRegionsSummary();
    currentCompanyId = Number.isInteger(companyId) && companyId > 0 ? companyId : null;
    document.getElementById("reportDownload").classList.toggle("hidden", currentCompanyId === null);
    document.getElementById("downloadReportStatus").textContent = "";
    document.getElementById("dashboard").classList.remove("hidden");

    document.getElementById("rows").textContent = data.rows.toLocaleString();
    document.getElementById("columns").textContent = data.columns.toLocaleString();
    document.getElementById("missing").textContent = data.missing_values.toLocaleString();
    document.getElementById("duplicates").textContent = data.duplicates.toLocaleString();
    document.getElementById("riskScore").textContent = data.risk_score;
    document.getElementById("analysisNote").textContent = data.note || "";

    renderAnomalies(data.anomalies);
    renderStatistics(data.statistics);
    renderRiskChart(data.risk_score);
    renderAiReport(report);

    window.scrollTo({
        top: document.getElementById("dashboard").offsetTop - 30,
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
    });
}

function renderAiReport(report) {
    const box = document.getElementById("aiReport");
    box.replaceChildren();
    box.classList.remove("structured-report");
    if (typeof report === "string") {
        const message = document.createElement("p");
        message.textContent = "Структурированный отчёт недоступен. Ответ сервиса:";
        const raw = document.createElement("div");
        raw.textContent = report;
        box.append(message, raw);
        return;
    }
    if (!report || !Number.isInteger(report.score) || report.score < 0 || report.score > 100
        || typeof report.recommendation?.needs_inspection !== "boolean"
        || typeof report.recommendation?.reason !== "string") {
        box.textContent = "Получен некорректный отчёт. Рекомендация о проверке недоступна.";
        return;
    }
    box.classList.add("structured-report");
    const list = document.createElement("ol");
    function addItem(label, value) {
        const item = document.createElement("li");
        const title = document.createElement("strong");
        title.textContent = `${label}: `;
        const content = document.createElement("span");
        content.textContent = value == null || value === "" ? "Не указано"
            : typeof value === "number" ? value.toLocaleString("ru-RU", { maximumFractionDigits: 20 })
            : String(value);
        item.append(title, content);
        list.appendChild(item);
        return item;
    }
    addItem("Название компании", report.company_name);
    addItem("Доход", report.revenue);
    addItem("Количество сотрудников", report.employees);
    addItem("Активность в социальных сетях", report.social_media);
    const scoreItem = addItem("Оценка риска", `${report.score}/100`);
    const bar = document.createElement("progress");
    bar.max = 100;
    bar.value = report.score;
    bar.setAttribute("aria-label", `Оценка риска: ${report.score} из 100`);
    scoreItem.appendChild(bar);
    const recommendation = addItem("Рекомендация", "");
    recommendation.lastChild.remove();
    const decision = document.createElement("p");
    decision.className = report.recommendation.needs_inspection
        ? "inspection-decision inspection-yes" : "inspection-decision inspection-no";
    decision.textContent = `Проверка нужна: ${report.recommendation.needs_inspection ? "Да" : "Нет"}`;
    const reason = document.createElement("p");
    reason.textContent = report.recommendation.reason;
    recommendation.append(decision, reason);
    box.appendChild(list);
}

function renderAnomalies(anomalies) {
    const box = document.getElementById("anomalies");
    box.innerHTML = "";

    if (!anomalies.length) {
        box.innerHTML = '<div class="empty">Аналитических сигналов не обнаружено.</div>';
        return;
    }

    anomalies.forEach(item => {
        const row = document.createElement("div");
        row.className = "anomaly";
        row.innerHTML = `
            <div>
                <strong>${escapeHtml(item.column)}</strong>
                <small>${escapeHtml(item.threshold)}</small>
            </div>
            <b>${item.count}</b>
        `;
        box.appendChild(row);
    });
}

function renderStatistics(statistics) {
    const tbody = document.getElementById("statistics");
    tbody.innerHTML = "";

    Object.entries(statistics).forEach(([name, value]) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${escapeHtml(name)}</td>
            <td>${value.mean ?? "—"}</td>
            <td>${value.median ?? "—"}</td>
            <td>${value.min ?? "—"}</td>
            <td>${value.max ?? "—"}</td>
            <td>${value.sum ?? "—"}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderRiskChart(score) {
    const ctx = document.getElementById("riskChart");

    if (riskChart) riskChart.destroy();

    riskChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Индикатор", "Остаток"],
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: ["#065084", "#dce3e0"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: "#344e56" }
                }
            }
        }
    });
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
