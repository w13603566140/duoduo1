/**
 * 看板页面 JS - 统计卡片、趋势图、排行表格
 */

let trendChart = null;

// === 页面初始化 ===
function domReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

domReady(() => {
    loadStats();
    loadRanking();
    loadTrend();
    loadProductFilter();

    // 自动刷新（每60秒）
    setInterval(() => {
        loadStats();
        loadRanking();
    }, 60000);
});

// === 加载统计卡片 ===
async function loadStats() {
    try {
        const resp = await fetch('/api/dashboard/stats');
        const data = await resp.json();

        document.getElementById('statProducts').textContent = data.total_products || 0;
        document.getElementById('statRecords').textContent = data.today_records || 0;
        document.getElementById('statAvgPrice').textContent = data.today_avg_price
            ? '¥' + Number(data.today_avg_price).toFixed(2)
            : '-';

        if (data.latest_scrape_raw) {
            const t = new Date(data.latest_scrape_raw);
            const now = new Date();
            const diffMin = Math.floor((now - t) / 60000);

            let text;
            if (diffMin < 1) text = '刚刚';
            else if (diffMin < 60) text = `${diffMin}分钟前`;
            else if (diffMin < 1440) text = `${Math.floor(diffMin / 60)}小时前`;
            else text = `${Math.floor(diffMin / 1440)}天前`;

            document.getElementById('statLastScrape').textContent = text;
        } else {
            document.getElementById('statLastScrape').textContent = '暂无';
        }
    } catch (e) {
        console.error('加载统计失败:', e);
    }
}

// === 加载排名表格 ===
async function loadRanking() {
    try {
        const today = new Date().toISOString().slice(0, 10);
        document.getElementById('rankingDate').textContent = `日期: ${today}`;

        const resp = await fetch(`/api/dashboard/ranking?limit=20`);
        const data = await resp.json();

        const tbody = document.getElementById('rankingTable');

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">暂无今日数据，请先执行采集</td></tr>';
            return;
        }

        tbody.innerHTML = data.map((item, i) => {
            const dailyBadge = item.daily_sales != null
                ? `<span class="badge bg-success">+${formatSales(item.daily_sales)}</span>`
                : '<span class="badge bg-secondary">新增</span>';

            const nameDisplay = item.product_name.length > 40
                ? item.product_name.slice(0, 40) + '...'
                : item.product_name;

            return `
                <tr onclick="window.location='/products/${item.product_id}'" style="cursor:pointer">
                    <td class="text-center fw-bold">${i + 1}</td>
                    <td class="product-name-cell" title="${escapeHtml(item.product_name)}">${escapeHtml(nameDisplay)}</td>
                    <td>${escapeHtml(item.shop_name || '-')}</td>
                    <td class="text-end">${formatPrice(item.price)}</td>
                    <td class="text-end fw-bold">${formatSales(item.sales_volume)}</td>
                    <td class="text-end">${dailyBadge}</td>
                    <td class="text-end"><small class="text-muted">${item.scrape_time || '-'}</small></td>
                </tr>`;
        }).join('');
    } catch (e) {
        console.error('加载排行失败:', e);
    }
}

// === 加载趋势图 ===
async function loadTrend() {
    try {
        const productId = document.getElementById('trendProductFilter')?.value || '';

        let url = '/api/dashboard/trend?days=30';
        if (productId) url += `&product_id=${productId}`;

        const resp = await fetch(url);
        const data = await resp.json();

        if (!data || data.length === 0) {
            return;
        }

        // 按日期+商品分组聚合
        const dateMap = {};
        const productSet = new Set();

        data.forEach(d => {
            if (!d.date) return;
            if (!dateMap[d.date]) dateMap[d.date] = {};
            dateMap[d.date][d.product_name || '商品'] = d.sales_volume;
            productSet.add(d.product_name || '商品');
        });

        const dates = Object.keys(dateMap).sort();
        const products = Array.from(productSet);

        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
                         '#1abc9c', '#e67e22', '#2980b9', '#27ae60', '#8e44ad'];

        const datasets = products.map((name, i) => ({
            label: name.length > 20 ? name.slice(0, 20) + '...' : name,
            data: dates.map(d => dateMap[d][name] || null),
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '20',
            fill: false,
            tension: 0.3,
            pointRadius: 2,
        }));

        const ctx = document.getElementById('trendChart').getContext('2d');

        if (trendChart) trendChart.destroy();

        trendChart = new Chart(ctx, {
            type: 'line',
            data: { labels: dates, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } },
                    tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${formatSales(ctx.parsed.y)}` } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: v => formatSales(v) }
                    }
                }
            }
        });
    } catch (e) {
        console.error('加载趋势图失败:', e);
    }
}

// === 加载商品下拉筛选 ===
async function loadProductFilter() {
    try {
        const resp = await fetch('/api/products?per_page=100');
        const data = await resp.json();

        const select = document.getElementById('trendProductFilter');
        if (!select) return;

        select.innerHTML = '<option value="">全部商品</option>';

        if (data.items) {
            data.items.forEach(p => {
                const name = p.product_name.length > 40 ? p.product_name.slice(0, 40) + '...' : p.product_name;
                select.innerHTML += `<option value="${p.id}">${escapeHtml(name)}</option>`;
            });
        }
    } catch (e) {
        console.error('加载商品列表失败:', e);
    }
}

// === 工具函数 ===
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
