/**
 * 商品列表 & 商品详情页 JS
 */

// ==================== 商品列表页 ====================
let productsPage = 1;
let searchTimeout = null;
let currentSort = 'last_seen';
let currentOrder = 'desc';

function sortProducts(field) {
    if (currentSort === field) {
        currentOrder = currentOrder === 'desc' ? 'asc' : 'desc';
    } else {
        currentSort = field;
        currentOrder = 'desc';
    }
    productsPage = 1;
    loadProducts();
    updateSortIcons();
}

function updateSortIcons() {
    document.querySelectorAll('.sortable .sort-icon').forEach(el => el.textContent = '');
    const th = document.querySelector(`.sortable[onclick*="${currentSort}"] .sort-icon`);
    if (th) th.textContent = currentOrder === 'desc' ? ' ▼' : ' ▲';
}

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        productsPage = 1;
        loadProducts();
    }, 500);
}

async function loadProducts(page = 1) {
    productsPage = page;
    const keyword = document.getElementById('searchInput')?.value || '';

    try {
        const resp = await fetch(`/api/products?page=${page}&per_page=20&keyword=${encodeURIComponent(keyword)}&sort_by=${currentSort}&sort_order=${currentOrder}`);
        const data = await resp.json();

        document.getElementById('productCount').textContent = `共 ${data.total} 个商品`;

        const tbody = document.getElementById('productsTable');
        if (!data.items || data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">暂无数据，请先执行采集</td></tr>';
            document.getElementById('pagination').innerHTML = '';
            return;
        }

        tbody.innerHTML = data.items.map(p => {
            const name = p.product_name.length > 35 ? p.product_name.slice(0, 35) + '...' : p.product_name;
            const shop = (p.shop_name || '').length > 12 ? (p.shop_name || '').slice(0, 12) + '...' : (p.shop_name || '-');
            const link = p.product_link ? '<a href="' + escapeHtml(p.product_link) + '" target="_blank" class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation()" title="打开商品链接">🔗</a>' : '-';

            return `
                <tr onclick="window.location='/products/${p.id}'" style="cursor:pointer">
                    <td class="product-name-cell" title="${escapeHtml(p.product_name)}">${escapeHtml(name)}</td>
                    <td><small title="${escapeHtml(p.shop_name || '')}">${escapeHtml(shop)}</small></td>
                    <td class="text-end">${formatPrice(p.latest_price)}</td>
                    <td class="text-end fw-bold">${formatSales(p.latest_sales_volume)}</td>
                    <td class="text-end"><span class="text-primary fw-bold">${formatSales(p.today_sales)}</span></td>
                    <td class="text-end">${formatSales(p.week_sales)}</td>
                    <td class="text-end">${formatSales(p.month_sales)}</td>
                    <td class=\"text-center\">${link}</td>
                    <td><a href="/products/${p.id}" class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation()">详情</a></td>
                </tr>`;
        }).join('');

        // 分页
        renderProductsPagination(data);
    } catch (e) {
        console.error('加载商品列表失败:', e);
    }
}

function renderProductsPagination(data) {
    const pag = document.getElementById('pagination');
    if (data.pages <= 1) { pag.innerHTML = ''; return; }

    let html = '';
    html += `<li class="page-item ${data.page <= 1 ? 'disabled' : ''}">
        <a class="page-link" href="javascript:void(0)" onclick="loadProducts(${data.page - 1})">上一页</a></li>`;

    for (let i = 1; i <= data.pages; i++) {
        if (i === 1 || i === data.pages || Math.abs(i - data.page) <= 2) {
            html += `<li class="page-item ${i === data.page ? 'active' : ''}">
                <a class="page-link" href="javascript:void(0)" onclick="loadProducts(${i})">${i}</a></li>`;
        } else if (Math.abs(i - data.page) === 3) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }

    html += `<li class="page-item ${data.page >= data.pages ? 'disabled' : ''}">
        <a class="page-link" href="javascript:void(0)" onclick="loadProducts(${data.page + 1})">下一页</a></li>`;

    pag.innerHTML = html;
}

// 页面初始化 - 兼容DOM已加载和未加载两种场景
function domReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

// 商品列表页初始化
if (document.getElementById('productsTable') && typeof PRODUCT_ID === 'undefined') {
    domReady(() => loadProducts());
}

// ==================== 商品详情页 ====================
let detailChart = null;

// 商品详情页初始化
if (typeof PRODUCT_ID !== 'undefined') {
    domReady(() => {
        loadProductInfo();
        loadProductHistory();
    });
}

async function loadProductInfo() {
    try {
        const resp = await fetch(`/api/products/${PRODUCT_ID}/info`);
        if (!resp.ok) {
            showToast('错误', '商品不存在', 'danger');
            return;
        }
        const data = await resp.json();

        document.getElementById('breadcrumbName').textContent = data.product_name.slice(0, 30);
        document.getElementById('chartProductName').textContent = data.product_name.slice(0, 20);
        document.getElementById('infoName').textContent = data.product_name;
        document.getElementById('infoShop').textContent = data.shop_name || '-';
        document.getElementById('infoKeyword').textContent = data.keyword || '-';
        document.getElementById('infoFirstSeen').textContent = data.first_seen || '-';
        document.getElementById('infoLastSeen').textContent = data.last_seen || '-';
        document.getElementById('infoPrice').textContent = formatPrice(data.latest_price);
        document.getElementById('infoVolume').textContent = formatSales(data.latest_sales_volume);
        document.getElementById('infoDaily').textContent = data.latest_daily_sales != null
            ? `+${formatSales(data.latest_daily_sales)}`
            : '-';
        document.getElementById('infoRaw').textContent = data.latest_raw_sales_text || '-';
        document.title = `${data.product_name.slice(0, 20)} - 拼多多监控`;
    } catch (e) {
        console.error('加载商品信息失败:', e);
    }
}

async function loadProductHistory() {
    try {
        const resp = await fetch(`/api/products/${PRODUCT_ID}/history?days=30`);
        const data = await resp.json();

        // 填充历史表格
        const tbody = document.getElementById('historyTable');
        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">暂无历史记录</td></tr>';
            return;
        }

        // 倒序显示（最新在前）
        const reversed = [...data].reverse();
        tbody.innerHTML = reversed.map(r => {
            const dailyBadge = r.daily_sales != null
                ? `<span class="badge bg-success">+${r.daily_sales}</span>`
                : '<span class="badge bg-secondary">-</span>';
            return `
                <tr>
                    <td>${r.scrape_date || '-'}</td>
                    <td><small>${r.scrape_time || '-'}</small></td>
                    <td class="text-end">${formatPrice(r.price)}</td>
                    <td class="text-end fw-bold">${formatSales(r.sales_volume)}</td>
                    <td class="text-end">${dailyBadge}</td>
                    <td class="text-end">${r.rank_position || '-'}</td>
                    <td><small>${r.raw_sales_text || '-'}</small></td>
                </tr>`;
        }).join('');

        // 绘制趋势图
        drawDetailChart(data);
    } catch (e) {
        console.error('加载历史记录失败:', e);
    }
}

function drawDetailChart(data) {
    if (!data || data.length === 0) return;

    const dates = data.map(d => d.date);
    const volumes = data.map(d => d.sales_volume);
    const dailySales = data.map(d => d.daily_sales);
    const prices = data.map(d => d.price);

    const ctx = document.getElementById('detailTrendChart').getContext('2d');

    if (detailChart) detailChart.destroy();

    detailChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: '累计销量',
                    data: volumes,
                    borderColor: '#e74c3c',
                    backgroundColor: '#e74c3c20',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y',
                    pointRadius: 2,
                },
                {
                    label: '日增量',
                    data: dailySales,
                    borderColor: '#2ecc71',
                    backgroundColor: '#2ecc7120',
                    fill: false,
                    tension: 0.3,
                    yAxisID: 'y1',
                    pointRadius: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const label = ctx.dataset.label || '';
                            const val = ctx.dataset.yAxisID === 'y1'
                                ? formatSales(ctx.parsed.y)
                                : (ctx.parsed.y >= 10000 ? (ctx.parsed.y / 10000).toFixed(1) + '万' : ctx.parsed.y);
                            return `${label}: ${val}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: '累计销量' },
                    ticks: { callback: v => formatSales(v) }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: '日增量' },
                    grid: { drawOnChartArea: false },
                    ticks: { callback: v => formatSales(v) }
                }
            }
        }
    });
}
