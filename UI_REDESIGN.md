# Обновление интерфейса ShadowAI

Фон `#edf0ee` получен из серо-бирюзовой палитры; поверхности `#fcfdfc`. Основные действия используют градиент `#0f828c` → `#065084`. Боковая панель — `#065084`, активный раздел — `#320A6B`, вспомогательные детали — `#788985`. Заголовки набраны PT Serif, интерфейс — PT Sans; шрифты загружаются через Google Fonts с системными запасными вариантами.

На широком экране панель открыта и сворачивается в полосу значков с подписями при наведении и фокусе. При ширине до 760 пикселей меню скрыто и открывается поверх страницы. Фон, ссылка и Escape закрывают меню; фокус удерживается внутри открытой панели. Учитывается настройка уменьшения движения.

Изменения Python ограничены двумя маршрутами информационных страниц. Расчёты, база, шифрование, отчёты и экспорт сохранены.

## static/style.css

```css
:root {
    --sage: #788985;
    --teal: #0f828c;
    --blue: #065084;
    --violet: #320A6B;
    --bg: #edf0ee;
    --surface: #fcfdfc;
    --text: #162d35;
    --muted: #435c61;
    --border: #c8d2ce;
    --rail: 264px;
}
* { box-sizing: border-box; }
body { margin: 0; color: var(--text); background: var(--bg); font: 17px/1.55 'PT Sans', 'Trebuchet MS', sans-serif; }
a { color: var(--blue); }
button, input, textarea, select { font: inherit; }
button, a, input, select, textarea { -webkit-tap-highlight-color: transparent; }
button { cursor: pointer; }
h1, h2, h3 { font-family: 'PT Serif', Georgia, serif; font-weight: 400; line-height: 1.2; }
h1 { font-size: clamp(34px, 4.6vw, 64px); letter-spacing: -.035em; margin: 18px 0 24px; }
h2 { font-size: clamp(25px, 2.5vw, 34px); margin: 0 0 18px; }
h3 { font-size: 24px; margin: 0 0 16px; }
p { margin: 0 0 18px; }
:focus-visible { outline: 3px solid var(--violet); outline-offset: 4px; }
[hidden], .hidden { display: none !important; }
.skip-link { position: fixed; left: 16px; top: -70px; z-index: 100; background: var(--surface); padding: 10px 18px; }
.skip-link:focus { top: 12px; }
.sidebar { position: fixed; inset: 0 auto 0 0; width: var(--rail); z-index: 40; display: flex; flex-direction: column; background: var(--blue); color: var(--surface); padding: 34px 20px; transition: width .22s ease, transform .22s ease; }
.brand { display: flex; gap: 12px; align-items: center; text-decoration: none; color: var(--surface); white-space: nowrap; margin-bottom: 64px; min-height: 40px; }
.brand-mark { width: 40px; height: 40px; flex: 0 0 40px; background: var(--surface); border-radius: 5px; }
.brand-name { font-size: 28px; font-weight: 700; letter-spacing: -.8px; }
.brand-name span { font-weight: 400; }
.sidebar nav { display: grid; gap: 8px; }
.nav-link { position: relative; display: flex; gap: 16px; align-items: center; min-height: 52px; padding: 12px; border-radius: 4px; color: var(--surface); text-decoration: none; white-space: nowrap; }
.nav-link svg { width: 24px; height: 24px; flex: 0 0 24px; }
.nav-link:hover { background: rgb(252 253 252 / .12); }
.nav-link.active { background: var(--violet); font-weight: 700; }
.nav-link.active::before { content: ''; position: absolute; left: -9px; top: 14px; bottom: 14px; width: 3px; background: var(--surface); }
.sidebar :focus-visible { outline-color: var(--surface); }
.sidebar-note { margin-top: auto; padding-top: 50px; font-size: 15px; line-height: 1.6; }
.sidebar-note-line { display: block; width: 38px; height: 3px; background: var(--sage); margin-bottom: 20px; }
.page-shell { margin-left: var(--rail); transition: margin-left .22s ease; }
.topbar { min-height: 80px; display: flex; align-items: center; gap: 18px; padding: 14px 4%; border-bottom: 1px solid var(--border); font-size: 15px; }
.prototype { margin-left: auto; color: var(--muted); font-size: 13px; }
button { border: 1px solid transparent; border-radius: 5px; padding: 12px 23px; font-weight: 700; color: #ffffff; background: linear-gradient(110deg, var(--teal), var(--blue)); transition: transform .15s ease, box-shadow .15s ease; }
button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 0 rgb(6 80 132 / .15); }
button:disabled { opacity: .55; cursor: wait; }
button.secondary { background: transparent; border-color: var(--border); color: var(--blue); padding: 9px 17px; }
.nav-toggle.secondary { display: grid; place-items: center; padding: 10px; border: 0; }
.sidebar-close { display: none; }
.nav-backdrop { position: fixed; inset: 0; background: rgb(22 45 53 / .56); border: 0; border-radius: 0; z-index: 35; }
.nav-backdrop:hover:not(:disabled) { transform: none; box-shadow: none; }
body.nav-collapsed { --rail: 88px; }
.nav-collapsed .sidebar { padding-inline: 20px; }
.nav-collapsed .brand-name, .nav-collapsed .sidebar-note { display: none; }
.nav-collapsed .nav-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.nav-collapsed .nav-link:hover .nav-label, .nav-collapsed .nav-link:focus-visible .nav-label { clip-path: none; width: max-content; height: auto; left: 60px; padding: 8px 14px; background: var(--violet); border-radius: 3px; }
main { width: min(1180px, 92%); margin: 0 auto; padding-bottom: 52px; min-height: calc(100vh - 170px); }
.hero { padding: 58px 0 44px; max-width: 860px; }
.hero p { color: var(--muted); font-size: 20px; max-width: 670px; }
.page-index { display: inline-block; color: var(--blue); border-bottom: 2px solid var(--teal); padding-bottom: 8px; font-size: 15px; }
.card { background: var(--surface); padding: clamp(22px, 3vw, 38px); margin-bottom: 26px; border: 1px solid var(--border); border-radius: 5px; min-width: 0; }
.card p { color: var(--muted); }
.upload { border-top: 4px solid var(--teal); }
.section-number { float: right; font-family: 'PT Serif', Georgia, serif; font-size: 28px; color: var(--teal); }
.file-label { display: block; margin: 25px 0 8px; font-weight: 700; }
.upload input { display: block; width: 100%; padding: 16px; margin-bottom: 20px; border: 1px dashed var(--sage); background: var(--bg); }
input::file-selector-button { font: inherit; color: var(--blue); background: var(--surface); border: 1px solid var(--border); padding: 8px 12px; margin-right: 14px; border-radius: 3px; cursor: pointer; }
.manual-card { background: transparent; border: 0; border-left: 3px solid var(--sage); border-radius: 0; margin: 38px 0 48px; scroll-margin-top: 24px; }
.manual-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 28px; margin-top: 25px; }
.manual-fields label { display: flex; flex-direction: column; gap: 8px; font-weight: 700; }
.manual-fields input, .manual-fields textarea, .manual-fields select, #reportFormat { width: 100%; min-width: 0; padding: 12px 14px; background: var(--surface); color: var(--text); border: 1px solid var(--sage); border-radius: 3px; font-weight: 400; }
.manual-fields textarea { resize: vertical; min-height: 118px; }
.manual-fields label:has(textarea) { grid-column: 1 / -1; }
.manual-fields + p { margin-top: 25px; }
::placeholder { color: var(--muted); opacity: 1; }
.section-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 16px; }
.section-head h2, .section-head h3 { margin: 0; }
.tag { color: var(--blue); background: var(--bg); padding: 5px 10px; font-size: 13px; font-weight: 700; white-space: nowrap; }
.tag.ai, .tag.warning { color: var(--violet); }
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); background: var(--blue); color: var(--surface); margin: 24px 0; }
.metric { padding: 22px 18px; border-right: 1px solid rgb(252 253 252 / .25); }
.metric:last-child { border: 0; }
.metric small { display: block; margin-bottom: 12px; font-size: 14px; }
.metric strong { font-size: 34px; font-weight: 400; }
.metric em { font-style: normal; font-size: 14px; }
.grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; }
.anomaly { border-left: 3px solid var(--violet); border-bottom: 1px solid var(--border); padding: 15px; margin-top: 12px; display: flex; justify-content: space-between; gap: 15px; }
.anomaly small { display: block; color: var(--muted); margin-top: 6px; }
.anomaly b { color: var(--violet); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 14px 12px; border-bottom: 1px solid var(--border); }
th { color: var(--blue); font-size: 14px; font-weight: 700; background: var(--bg); }
.ai-card { border-top: 3px solid var(--violet); }
.report { margin-top: 20px; white-space: pre-wrap; line-height: 1.7; overflow-wrap: anywhere; }
.structured-report { white-space: normal; }
.structured-report ol { padding-left: 24px; margin: 0; }
.structured-report li { padding: 12px 0; border-bottom: 1px solid var(--border); }
.structured-report li:last-child { border: 0; }
.structured-report progress { display: block; width: 100%; height: 13px; margin-top: 12px; accent-color: var(--blue); }
.inspection-decision { padding: 12px 16px; border-left: 4px solid var(--violet); font-weight: 700; background: var(--bg); }
.inspection-no { border-color: var(--teal); }
.notice { border-left: 3px solid var(--violet); padding: 18px 22px; background: var(--surface); }
.loading, .empty, #downloadReportStatus, #regionsStatus, #graphStatus { color: var(--muted); margin-top: 12px; font-size: 15px; }
.regions-scroll { max-height: 600px; overflow-y: auto; }
#companyGraph { width: 100%; height: auto; min-height: 240px; }
#companyGraph [role="button"] { cursor: pointer; }
#companyGraph [role="button"]:focus circle { stroke: var(--text); stroke-width: 4px; }
#graphDetails { margin-top: 12px; overflow-wrap: anywhere; font-weight: 700; }
#reportFormat { width: auto; margin: 10px 14px; }
.editorial-panel { background: var(--surface); border-top: 3px solid var(--teal); padding: clamp(24px, 4vw, 48px); }
.editorial-panel h2:not(:first-child) { margin-top: 36px; }
.placeholder-notice { color: var(--violet); max-width: 680px; }
.contact-list { margin: 30px 0 0; }
.contact-list div { display: grid; grid-template-columns: 200px 1fr; gap: 20px; padding: 23px 0; border-top: 1px solid var(--border); }
.contact-list dt { font-weight: 700; color: var(--blue); }
.contact-list dd { margin: 0; overflow-wrap: anywhere; }
.about-layout { display: grid; grid-template-columns: 1.7fr 1fr; gap: 28px; }
.principle-panel { background: var(--violet); color: var(--surface); padding: 36px; align-self: start; }
.principle-number { font-family: 'PT Serif', Georgia, serif; display: block; font-size: 50px; margin-bottom: 30px; }
.page-footer { border-top: 1px solid var(--border); padding: 22px 4%; display: flex; gap: 24px; font-size: 14px; color: var(--muted); }
.page-footer span { margin-left: auto; }
@media (max-width: 1100px) {
    :root { --rail: 230px; }
    .prototype { display: none; }
    .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .grid, .about-layout { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
    body, body.nav-collapsed { --rail: 0px; }
    .sidebar, .nav-collapsed .sidebar { width: min(300px, 86vw); transform: translateX(-100%); padding: 26px 22px; visibility: hidden; }
    body.nav-open { overflow: hidden; }
    .nav-open .sidebar { transform: translateX(0); visibility: visible; }
    .sidebar .brand { margin-bottom: 24px; }
    .nav-collapsed .brand-name { display: inline; }
    .nav-collapsed .sidebar-note { display: block; }
    .nav-collapsed .nav-label { position: static; clip-path: none; width: auto; height: auto; }
    .sidebar-close.secondary { display: block; color: var(--surface); margin: 0 0 24px; }
    .topbar { min-height: 65px; padding: 10px 4%; font-size: 13px; gap: 10px; }
    .hero { padding: 35px 0 28px; }
    .hero p { font-size: 18px; }
    .manual-fields { grid-template-columns: 1fr; }
    .section-head { align-items: flex-start; flex-wrap: wrap; }
    .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .metric { padding: 18px; }
    .contact-list div { grid-template-columns: 1fr; gap: 6px; }
    #reportFormat { margin-left: 0; }
    #reportDownload label { display: block; }
    .page-footer { flex-direction: column; gap: 4px; }
    .page-footer span { margin: 0; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; animation: none !important; scroll-behavior: auto !important; }
}
```

## templates/base.html

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Главная{% endblock %} — ShadowAI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&family=PT+Serif:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
<a class="skip-link" href="#mainContent">Перейти к содержанию</a>
<aside id="sidebar" class="sidebar" aria-label="Навигация">
    <a class="brand" href="{{ url_for('index') }}" aria-label="ShadowAI — главная">
        <svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true">
            <path d="M5 6h27v8H13v7H5z" fill="#788985"/>
            <path d="M8 26h19v-7h8v15H8z" fill="#0f828c"/>
            <path d="M17 16h7v8h-7z" fill="#320A6B"/>
        </svg>
        <span class="brand-name">Shadow<span>AI</span></span>
    </a>
    <button id="closeSidebar" class="sidebar-close secondary" type="button" aria-label="Закрыть меню">Закрыть</button>
    <nav aria-label="Основная навигация">
        {% set items = [
            ('index', 'Главная', url_for('index'), 'M3 10 12 3l9 7v11h-6v-7H9v7H3z'),
            ('manual', 'Ручной ввод', url_for('index') ~ '#manual-entry', 'm4 16-1 5 5-1L21 7l-4-4z M14 6l4 4'),
            ('contacts', 'Контакты', url_for('contacts'), 'M3 5h18v14H3z M3 6l9 7 9-7'),
            ('about', 'О нас', url_for('about'), 'M12 10v7 M12 6v1 M3 3h18v18H3z')
        ] %}
        {% for key, label, href, path in items %}
        <a class="nav-link{% if request.endpoint == key %} active{% endif %}"
           href="{{ href }}" data-page="{{ key }}" title="{{ label }}"
           {% if request.endpoint == key %}aria-current="page"{% endif %}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="{{ path }}"/></svg>
            <span class="nav-label">{{ label }}</span>
        </a>
        {% endfor %}
    </nav>
    <div class="sidebar-note"><span class="sidebar-note-line"></span>Данные для анализа.<br>Решения — за человеком.</div>
</aside>
<button id="navBackdrop" class="nav-backdrop" type="button" aria-label="Закрыть меню" tabindex="-1" hidden></button>
<div id="pageShell" class="page-shell">
    <header class="topbar">
        <button id="navToggle" class="nav-toggle secondary" type="button" aria-controls="sidebar" aria-expanded="true" aria-label="Свернуть меню">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
        </button>
        <span>Мониторинг неформальной экономики</span>
        <span class="prototype">Исследовательский прототип</span>
    </header>
    <main id="mainContent" tabindex="-1">{% block content %}{% endblock %}</main>
    <footer class="page-footer">ShadowAI <span>Аналитический сигнал — не юридическое заключение.</span></footer>
</div>
<script src="{{ url_for('static', filename='nav.js') }}"></script>
{% block scripts %}{% endblock %}
</body>
</html>
```

## templates/index.html

```html
{% extends 'base.html' %}
{% block title %}Главная{% endblock %}
{% block head %}<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>{% endblock %}
{% block content %}
    <section class="hero">
        <span class="page-index">Рабочее пространство аналитика</span>
        <h1>Мониторинг<br>неформальной экономики</h1>
        <p>От исходных данных к объяснимым сигналам: загрузите таблицу или добавьте сведения о компании вручную.</p>
    </section>

    <section class="card upload" aria-labelledby="uploadHeading">
        <div class="section-number">01</div><h2 id="uploadHeading">Начните с данных</h2>
        <p>CSV, XLSX или XLS. Для демо можно использовать любой обезличенный набор данных.</p>
        <label class="file-label" for="fileInput">Таблица для анализа</label>
        <input id="fileInput" type="file" accept=".csv,.xlsx,.xls">
        <button id="analyzeButton" onclick="analyzeData()">Проанализировать файл</button>
        <div id="loading" class="loading hidden">Обработка данных...</div>
    </section>

    {% include 'manual_entry.html' %}

    <section class="card" aria-labelledby="regionsHeading">
        <div class="section-head">
            <h2 id="regionsHeading">Карта риска по регионам</h2>
            <button class="secondary" id="refreshRegionsButton" type="button">Обновить</button>
        </div>
        <p>Средняя оценка риска: бирюзовый — ниже 30, синий — от 30 до 71 (не включая 71), фиолетовый — от 71.
            Записи без оценки не входят в среднее. Высокий риск — от 71 балла.</p>
        <div id="regionsStatus" role="status" aria-live="polite">Загрузка сводки...</div>
        <div class="regions-scroll">
            <div id="regionsChartContainer" class="hidden" style="position: relative; height: 240px;">
                <canvas id="regionsChart" role="img" aria-label="Средняя оценка риска по регионам"></canvas>
            </div>
        </div>
    </section>

    <section class="card" aria-labelledby="graphHeading">
        <div class="section-head">
            <h2 id="graphHeading">Граф связей</h2>
            <button class="secondary" id="refreshGraphButton" type="button">Обновить</button>
        </div>
        <p>Сплошная линия — одинаковый телефон, пунктир — одинаковое значение соцсетей.
            Совпадение не доказывает, что записи относятся к одной компании.
            Значения «низкая», «средняя», «высокая» также участвуют в сравнении.</p>
        <p>Цвет узла: бирюзовый — ниже 30, синий — от 30 до 71 (не включая 71),
            фиолетовый — от 71, серо-бирюзовый — оценка отсутствует.</p>
        <div id="graphStatus" role="status" aria-live="polite">Загрузка связей...</div>
        <svg id="companyGraph" class="hidden" viewBox="0 0 900 460"
             aria-label="Граф связей компаний"></svg>
        <div id="graphDetails" role="status" aria-live="polite"></div>
    </section>

    <section id="dashboard" class="hidden">
        <div id="reportDownload" class="card hidden">
            <label for="reportFormat">Скачать отчёт</label>
            <select id="reportFormat">
                <option value="pdf">PDF</option>
                <option value="xlsx">Excel (.xlsx)</option>
                <option value="csv">CSV</option>
            </select>
            <button id="downloadReportButton" type="button">Скачать</button>
            <div id="downloadReportStatus" role="status" aria-live="polite"></div>
        </div>
        <div class="section-head">
            <h2>Аналитическая панель</h2>
            <span class="tag">Результаты</span>
        </div>

        <div class="metrics">
            <div class="metric"><small>Записей</small><strong id="rows">0</strong></div>
            <div class="metric"><small>Столбцов</small><strong id="columns">0</strong></div>
            <div class="metric"><small>Пропуски</small><strong id="missing">0</strong></div>
            <div class="metric"><small>Дубликаты</small><strong id="duplicates">0</strong></div>
            <div class="metric"><small>Оценка риска</small><strong id="riskScore">0</strong><em>/100</em></div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="section-head">
                    <h3>Аномалии</h3>
                    <span class="tag warning">Проверка</span>
                </div>
                <p id="analysisNote"></p>
                <div id="anomalies"></div>
            </div>

            <div class="card">
                <h3>Распределение риска</h3>
                <canvas id="riskChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h3>Статистика числовых показателей</h3>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Показатель</th>
                            <th>Среднее</th>
                            <th>Медиана</th>
                            <th>Минимум</th>
                            <th>Максимум</th>
                            <th>Сумма</th>
                        </tr>
                    </thead>
                    <tbody id="statistics"></tbody>
                </table>
            </div>
        </div>

        <div class="card ai-card">
            <div class="section-head">
                <h3>Аналитическое заключение</h3>
                <span class="tag ai">Отчёт</span>
            </div>
            <div id="aiReport" class="report">Ожидание...</div>
        </div>

        <div class="notice">
            <strong>Важно:</strong>
            статистическая аномалия не является доказательством незаконной деятельности.
            Результаты системы предназначены для аналитической проверки.
        </div>
    </section>
{% endblock %}
{% block scripts %}<script src="{{ url_for('static', filename='app.js') }}"></script>{% endblock %}
```

## templates/contacts.html

```html
{% extends 'base.html' %}
{% block title %}Контакты{% endblock %}
{% block content %}
<section class="hero compact">
    <span class="page-index">Связь с командой</span>
    <h1>Контакты</h1>
    <p>Вопросы о данных, работе платформы и совместной проверке результатов.</p>
</section>
<section class="editorial-panel">
    <h2>Контактная информация</h2>
    <p class="placeholder-notice">Это поля-заглушки. Перед публикацией замените их реальными контактами команды.</p>
    <dl class="contact-list">
        <div><dt>Организация</dt><dd>[Укажите название организации]</dd></div>
        <div><dt>Электронная почта</dt><dd>[Укажите электронную почту]</dd></div>
        <div><dt>Телефон</dt><dd>[Укажите контактный телефон]</dd></div>
        <div><dt>Адрес</dt><dd>[Укажите адрес организации]</dd></div>
    </dl>
</section>
{% endblock %}
```

## templates/about.html

```html
{% extends 'base.html' %}
{% block title %}О нас{% endblock %}
{% block content %}
<section class="hero compact">
    <span class="page-index">О проекте</span>
    <h1>Данные помогают<br>задать точный вопрос.</h1>
    <p>ShadowAI — прототип платформы мониторинга неформальной экономики для задачи хакатона.</p>
</section>
<div class="about-layout">
    <section class="editorial-panel">
        <h2>Что мы проверяем</h2>
        <p>Платформа принимает таблицу или сведения об одной компании. Она ищет пропуски, дубликаты, статистические отклонения и признаки торговой активности при низкой заявленной выручке.</p>
        <p>Сводка по регионам помогает сравнить сохранённые записи. Граф показывает совпадения телефонов и значений соцсетей. Совпадение само по себе не подтверждает связь между компаниями.</p>
        <h2>Как использовать результат</h2>
        <p>Оценка риска помогает выбрать данные для дополнительной сверки. Отчёт объясняет обнаруженные сигналы; его можно скачать и передать специалисту для рассмотрения.</p>
    </section>
    <aside class="principle-panel">
        <span class="principle-number">01</span>
        <h2>Проверять,<br>а не обвинять</h2>
        <p>Демонстрационные пороги не учитывают все особенности отрасли и налогового режима. Окончательные выводы требуют проверки исходных данных человеком.</p>
    </aside>
</div>
{% endblock %}
```

## static/nav.js

```javascript
(() => {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('navToggle');
    const close = document.getElementById('closeSidebar');
    const backdrop = document.getElementById('navBackdrop');
    const shell = document.getElementById('pageShell');
    const mobile = window.matchMedia('(max-width: 760px)');
    let collapsed = false;
    let opened = false;

    function sync() {
        document.body.classList.toggle('nav-collapsed', !mobile.matches && collapsed);
        document.body.classList.toggle('nav-open', mobile.matches && opened);
        backdrop.hidden = !mobile.matches || !opened;
        sidebar.inert = mobile.matches && !opened;
        shell.inert = mobile.matches && opened;
        toggle.setAttribute('aria-expanded', String(mobile.matches ? opened : !collapsed));
        toggle.setAttribute('aria-label', mobile.matches ? 'Открыть меню' : collapsed ? 'Развернуть меню' : 'Свернуть меню');
        if (mobile.matches && opened) {
            sidebar.setAttribute('role', 'dialog');
            sidebar.setAttribute('aria-modal', 'true');
        } else {
            sidebar.removeAttribute('role');
            sidebar.removeAttribute('aria-modal');
        }
    }
    function dismiss(returnFocus = true) {
        opened = false;
        sync();
        if (returnFocus) toggle.focus();
    }
    toggle.addEventListener('click', () => {
        if (mobile.matches) {
            opened = !opened;
            sync();
            if (opened) close.focus();
        } else {
            collapsed = !collapsed;
            sync();
        }
    });
    close.addEventListener('click', () => dismiss());
    backdrop.addEventListener('click', () => dismiss());
    sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
        if (mobile.matches) {
            dismiss(false);
            if (link.hash && link.pathname === window.location.pathname) {
                const target = document.getElementById(link.hash.slice(1));
                if (target) { target.setAttribute('tabindex', '-1'); target.focus({ preventScroll: true }); }
            }
        }
    }));
    document.addEventListener('keydown', event => {
        if (!mobile.matches || !opened) return;
        if (event.key === 'Escape') { dismiss(); return; }
        if (event.key !== 'Tab') return;
        const focusable = [...sidebar.querySelectorAll('a, button')].filter(item => item.getClientRects().length);
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    mobile.addEventListener('change', () => {
        const focusWasInside = sidebar.contains(document.activeElement);
        opened = false;
        sync();
        if (mobile.matches && focusWasInside) toggle.focus();
    });
    function activeLink() {
        if (window.location.pathname !== '/') return;
        const selected = window.location.hash === '#manual-entry' ? 'manual' : 'index';
        sidebar.querySelectorAll('.nav-link').forEach(link => {
            const active = link.dataset.page === selected;
            link.classList.toggle('active', active);
            if (active) link.setAttribute('aria-current', selected === 'manual' ? 'location' : 'page');
            else link.removeAttribute('aria-current');
        });
    }
    window.addEventListener('hashchange', activeLink);
    sync();
    activeLink();
})();
```

## templates/manual_entry.html

```html
<section class="card manual-card" id="manual-entry" aria-labelledby="manualHeading">
    <div class="section-number">02</div><h2 id="manualHeading">Одна компания — подробнее</h2>
    <p>Укажите выручку и налоговую долю за один и тот же период. Поля со звёздочкой обязательны.</p>
    <form id="manualEntryForm" novalidate>
        <div class="manual-fields">
            <label>Название компании *
                <input name="name" type="text" required placeholder="Например, ООО «Пример»">
            </label>
            <label>Доход / выручка *
                <input name="revenue" type="number" min="0" step="any" required>
            </label>
            <label>Налог, % *
                <input name="tax_percent" type="number" min="0" max="100" step="any" required>
            </label>
            <label>Количество сотрудников *
                <input name="employees" type="number" min="0" max="9007199254740991" step="1" required>
            </label>
            <label>Активность в соцсетях
                <textarea name="social_media" rows="4"
                          placeholder="Например: В наличии новые товары, доставка, скидка при заказе"></textarea>
            </label>
            <label>Регион (необязательно)
                <input name="region" type="text" placeholder="Например, Ташкент">
            </label>
            <label>Телефон (необязательно)
                <input name="phone" type="tel" placeholder="Например, +998901234567">
            </label>
            <label>Отрасль (необязательно)
                <input name="sector" type="text" placeholder="Например, торговля">
            </label>
        </div>
        <p>Оценка демонстрационная: пороги не учитывают отрасль и налоговый режим.</p>
        <p>Торговые слова в соцсетях при выручке до 1 000 включительно добавляют 15 баллов.
            Это демонстрационный порог в единицах введённой выручки.</p>
        <button id="manualEntryButton" type="submit">Сохранить и проанализировать</button>
        <div id="manualEntryStatus" class="loading" role="status" aria-live="polite"></div>
    </form>
</section>
```

## Новые маршруты app.py

```python
@app.get("/contacts")
def contacts():
    return render_template("contacts.html")


@app.get("/about")
def about():
    return render_template("about.html")
```

## Визуальные изменения static/app.js

Цвета низкого, среднего и высокого риска заменены на `#0f828c`, `#065084`, `#320A6B`; неопределённого — на `#788985`. Подписи и легенды обновлены. Для кольцевой диаграммы задана та же палитра. Метка Score переведена как «Оценка риска». Прокрутка и анимация графа учитывают prefers-reduced-motion. Обработчики запросов, формы и API не изменены.

## Проверка

18 существующих серверных тестов прошли. Все три страницы отвечают 200; ID уникальны, аналитический JS подключён только на главной. Синтаксис JavaScript проверен. Смоделированы переключение панели, мобильное открытие, закрытие фоном/Escape и переход к форме. Контраст текста 12,53:1, вторичного текста 6,22:1, текста основных кнопок не ниже 4,57:1. Визуальная проверка в браузере не выполнена: браузеры в среде недоступны.
