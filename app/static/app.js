const money = value => `S/ ${Number(value).toFixed(2)}`;
const rows = window.expenseRows || [];
const monthNames = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];

let activeView = "category";
let expenseChart = null;
const ctx = document.getElementById("expenseChart");
const categorySelect = document.getElementById("chartCategory");
const monthSelect = document.getElementById("chartMonth");
const yearSelect = document.getElementById("chartYear");
const monthLabel = document.getElementById("monthFilterLabel");
const summary = document.getElementById("chartSummary");

function filteredRows() {
  const category = categorySelect.value;
  return rows.filter(r => category === "Todas" || r.category === category);
}
function aggregate(items, keyFn, labels) {
  const map = new Map(labels.map(label => [label, 0]));
  items.forEach(item => {
    const key = keyFn(item);
    map.set(key, (map.get(key) || 0) + Number(item.amount));
  });
  return {labels:[...map.keys()], values:[...map.values()]};
}
function renderChart() {
  const selectedYear = Number(yearSelect.value);
  const selectedMonth = Number(monthSelect.value);
  let items = filteredRows();
  let result, type = "bar", title = "";

  monthLabel.style.display = activeView === "day" || activeView === "category" ? "" : "none";

  if (activeView === "category") {
    items = items.filter(r => {
      const d = new Date(`${r.date}T00:00:00`);
      return d.getFullYear() === selectedYear && d.getMonth()+1 === selectedMonth;
    });
    const categories = [...new Set(items.map(r => r.category))];
    result = aggregate(items, r => r.category, categories);
    type = "doughnut";
    title = `${monthNames[selectedMonth-1]} ${selectedYear}`;
  } else if (activeView === "day") {
    items = items.filter(r => {
      const d = new Date(`${r.date}T00:00:00`);
      return d.getFullYear() === selectedYear && d.getMonth()+1 === selectedMonth;
    });
    const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
    const labels = Array.from({length:daysInMonth},(_,i)=>String(i+1));
    result = aggregate(items, r => String(new Date(`${r.date}T00:00:00`).getDate()), labels);
    type = "line"; title = `Gasto diario · ${monthNames[selectedMonth-1]} ${selectedYear}`;
  } else if (activeView === "month") {
    items = items.filter(r => new Date(`${r.date}T00:00:00`).getFullYear() === selectedYear);
    result = aggregate(items, r => monthNames[new Date(`${r.date}T00:00:00`).getMonth()], monthNames);
    type = "bar"; title = `Gasto mensual · ${selectedYear}`;
  } else {
    const years = [...new Set(rows.map(r => new Date(`${r.date}T00:00:00`).getFullYear()))].sort();
    result = aggregate(items, r => String(new Date(`${r.date}T00:00:00`).getFullYear()), years.map(String));
    type = "bar"; title = "Comparación anual";
  }

  const total = result.values.reduce((a,b)=>a+b,0);
  const nonZero = result.values.filter(v=>v>0);
  const average = nonZero.length ? total/nonZero.length : 0;
  summary.textContent = `${title} · Total ${money(total)} · Promedio ${money(average)}`;

  if (expenseChart) expenseChart.destroy();
  expenseChart = new Chart(ctx,{
    type,
    data:{labels:result.labels,datasets:[{label:"Gastos",data:result.values}]},
    options:{
      responsive:true,maintainAspectRatio:false,
      scales:type==="doughnut"?{}:{y:{beginAtZero:true}},
      plugins:{legend:{display:type==="doughnut",position:"bottom"},tooltip:{callbacks:{label:c=>`${c.label}: ${money(c.raw)}`}}}
    }
  });
}
document.querySelectorAll(".chart-tab").forEach(btn => btn.addEventListener("click",()=>{
  document.querySelectorAll(".chart-tab").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active"); activeView=btn.dataset.view; renderChart();
}));
[categorySelect,monthSelect,yearSelect].forEach(el=>el?.addEventListener("change",renderChart));
if(ctx) renderChart();

const search=document.getElementById("search"),table=document.getElementById("transactions-table");
if(search&&table) search.addEventListener("input",()=>{
  const term=search.value.toLowerCase().trim();
  table.querySelectorAll("tbody tr").forEach(row=>row.style.display=row.textContent.toLowerCase().includes(term)?"":"none");
});

const typeFilter=document.getElementById("insightTypeFilter");
const statusFilter=document.getElementById("insightStatusFilter");
function filterInsights(){
  document.querySelectorAll(".history-item").forEach(item=>{
    const typeOk=typeFilter.value==="Todos"||item.dataset.type===typeFilter.value;
    const statusOk=statusFilter.value==="Todos"||item.dataset.status===statusFilter.value;
    item.style.display=typeOk&&statusOk?"":"none";
  });
}
[typeFilter,statusFilter].forEach(el=>el?.addEventListener("change",filterInsights));


// Tema oscuro persistente.
const themeToggle = document.getElementById("themeToggle");
const storedTheme = localStorage.getItem("finance-theme");
if (storedTheme === "dark") {
  document.documentElement.dataset.theme = "dark";
  if (themeToggle) themeToggle.textContent = "☀️";
}
themeToggle?.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme !== "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  localStorage.setItem("finance-theme", dark ? "dark" : "light");
  themeToggle.textContent = dark ? "☀️" : "🌙";
});

// Toasts temporales.
document.querySelectorAll(".toast-container .success, .toast-container .error").forEach(toast => {
  toast.classList.add("toast");
  setTimeout(() => toast.classList.add("toast-visible"), 50);
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    setTimeout(() => toast.remove(), 300);
  }, 4200);
});

// Ordenamiento local de movimientos.
document.querySelectorAll(".sort-button").forEach(button => {
  let ascending = true;
  button.addEventListener("click", () => {
    const tbody = document.querySelector("#transactions-table tbody");
    if (!tbody) return;
    const column = Number(button.dataset.column);
    const numeric = button.dataset.number === "true";
    const rows = [...tbody.querySelectorAll("tr")].filter(row => row.children.length > 1);
    rows.sort((a, b) => {
      let left = a.children[column]?.textContent.trim() || "";
      let right = b.children[column]?.textContent.trim() || "";
      if (numeric) {
        left = Number(left.replace(/[^\d.-]/g, ""));
        right = Number(right.replace(/[^\d.-]/g, ""));
        return ascending ? left - right : right - left;
      }
      return ascending
        ? left.localeCompare(right, "es", {numeric: true})
        : right.localeCompare(left, "es", {numeric: true});
    });
    rows.forEach(row => tbody.appendChild(row));
    ascending = !ascending;
  });
});
