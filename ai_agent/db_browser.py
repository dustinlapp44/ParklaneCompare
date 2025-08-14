#!/usr/bin/env python3
"""
Modern Database Browser with Pagination and Column Search
"""

from flask import Flask, render_template_string, request, jsonify
import sqlite3
import math
from datetime import datetime

app = Flask(__name__)

DB_PATH = "/tmp/payments.db"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Database Browser</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f5f5f5; 
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 20px; 
            text-align: center; 
        }
        .header h1 { margin: 0; font-size: 2rem; }
        .stats-section { 
            padding: 20px; 
            background: #f8f9fa; 
            border-bottom: 1px solid #dee2e6; 
        }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
        }
        .stat-card { 
            background: white; 
            padding: 15px; 
            border-radius: 6px; 
            border-left: 4px solid #007bff; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stat-card h3 { margin: 0 0 5px 0; font-size: 0.9rem; color: #666; }
        .stat-card .value { font-size: 1.5rem; font-weight: bold; color: #333; }
        
        .table-section { 
            padding: 20px; 
        }
        .table-controls { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 20px; 
            flex-wrap: wrap; 
            gap: 10px; 
        }
        .table-title { 
            font-size: 1.5rem; 
            font-weight: bold; 
            color: #333; 
        }
        .global-search { 
            display: flex; 
            align-items: center; 
            gap: 10px; 
        }
        .search-input { 
            padding: 8px 12px; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            font-size: 14px; 
            width: 250px; 
        }
        .search-btn { 
            padding: 8px 16px; 
            background: #007bff; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 14px; 
        }
        .search-btn:hover { background: #0056b3; }
        .clear-btn { 
            padding: 8px 16px; 
            background: #6c757d; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 14px; 
        }
        .clear-btn:hover { background: #545b62; }
        
        .table-wrapper { 
            overflow-x: auto; 
            border: 1px solid #dee2e6; 
            border-radius: 6px; 
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            background: white; 
        }
        th { 
            background: #f8f9fa; 
            padding: 12px 8px; 
            text-align: left; 
            font-weight: 600; 
            color: #495057; 
            border-bottom: 2px solid #dee2e6; 
            position: sticky; 
            top: 0; 
            z-index: 10; 
        }
        td { 
            padding: 12px 8px; 
            border-bottom: 1px solid #f1f3f4; 
            vertical-align: top; 
        }
        tr:hover { background: #f8f9fa; }
        .column-search { 
            width: 100%; 
            padding: 4px 6px; 
            border: 1px solid #ccc; 
            border-radius: 3px; 
            font-size: 12px; 
            margin-top: 4px; 
        }
        
        .pagination { 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            margin-top: 20px; 
            gap: 10px; 
        }
        .pagination button { 
            padding: 8px 12px; 
            border: 1px solid #dee2e6; 
            background: white; 
            cursor: pointer; 
            border-radius: 4px; 
        }
        .pagination button:hover { background: #f8f9fa; }
        .pagination button:disabled { 
            opacity: 0.5; 
            cursor: not-allowed; 
        }
        .pagination .current { 
            background: #007bff; 
            color: white; 
            border-color: #007bff; 
        }
        .page-info { 
            color: #666; 
            font-size: 14px; 
        }
        
        .loading { 
            text-align: center; 
            padding: 40px; 
            color: #666; 
        }
        .error { 
            background: #f8d7da; 
            color: #721c24; 
            padding: 15px; 
            border-radius: 4px; 
            margin: 20px 0; 
        }
        
        .table-tabs { 
            display: flex; 
            border-bottom: 1px solid #dee2e6; 
            margin-bottom: 20px; 
        }
        .tab { 
            padding: 12px 20px; 
            cursor: pointer; 
            border-bottom: 2px solid transparent; 
            color: #666; 
            font-weight: 500; 
        }
        .tab.active { 
            color: #007bff; 
            border-bottom-color: #007bff; 
        }
        .tab:hover { background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗄️ Database Browser</h1>
            <p>Modern interface for browsing payment and invoice data</p>
        </div>
        
        <div class="stats-section">
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <h3>Loading...</h3>
                    <div class="value">-</div>
                </div>
            </div>
        </div>
        
        <div class="table-section">
            <div class="table-tabs">
                <div class="tab active" onclick="switchTable('invoices')">📄 Invoices</div>
                <div class="tab" onclick="switchTable('payments')">💳 Payments</div>
            </div>
            
            <div class="table-controls">
                <div class="table-title" id="tableTitle">Invoices</div>
                <div class="global-search">
                    <input type="text" id="globalSearch" class="search-input" placeholder="Global search...">
                    <button class="search-btn" onclick="searchTable()">🔍 Search</button>
                    <button class="clear-btn" onclick="clearSearch()">Clear</button>
                </div>
            </div>
            
            <div class="table-wrapper">
                <div id="tableContent" class="loading">Loading data...</div>
            </div>
            
            <div class="pagination" id="pagination" style="display: none;">
                <button onclick="goToPage(1)" id="firstBtn">First</button>
                <button onclick="goToPage(currentPage - 1)" id="prevBtn">Previous</button>
                <span class="page-info" id="pageInfo">Page 1 of 1</span>
                <button onclick="goToPage(currentPage + 1)" id="nextBtn">Next</button>
                <button onclick="goToPage(totalPages)" id="lastBtn">Last</button>
            </div>
        </div>
    </div>

    <script>
        let currentTable = 'invoices';
        let currentPage = 1;
        let totalPages = 1;
        let pageSize = 50;
        let currentFilters = {};
        let globalSearchTerm = '';
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            loadStats();
            loadTableData();
        });
        
        function loadStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('statsGrid').innerHTML = 
                            '<div class="error">Error loading stats: ' + data.error + '</div>';
                        return;
                    }
                    
                    document.getElementById('statsGrid').innerHTML = `
                        <div class="stat-card">
                            <h3>Total Invoices</h3>
                            <div class="value">${data.invoices.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Payments</h3>
                            <div class="value">${data.payments.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Unpaid Invoices</h3>
                            <div class="value">${data.unpaid_invoices.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Paid Invoices</h3>
                            <div class="value">${data.paid_invoices.toLocaleString()}</div>
                        </div>
                    `;
                })
                .catch(error => {
                    document.getElementById('statsGrid').innerHTML = 
                        '<div class="error">Error loading stats: ' + error + '</div>';
                });
        }
        
        function switchTable(tableName) {
            currentTable = tableName;
            currentPage = 1;
            currentFilters = {};
            globalSearchTerm = '';
            
            // Update tab appearance
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update title
            document.getElementById('tableTitle').textContent = 
                tableName.charAt(0).toUpperCase() + tableName.slice(1);
            
            // Clear search
            document.getElementById('globalSearch').value = '';
            
            loadTableData();
        }
        
        function loadTableData() {
            document.getElementById('tableContent').innerHTML = '<div class="loading">Loading data...</div>';
            document.getElementById('pagination').style.display = 'none';
            
            const params = new URLSearchParams({
                table: currentTable,
                page: currentPage,
                size: pageSize,
                global_search: globalSearchTerm
            });
            
            // Add column filters
            Object.keys(currentFilters).forEach(column => {
                if (currentFilters[column]) {
                    params.append(`filter_${column}`, currentFilters[column]);
                }
            });
            
            fetch('/api/table?' + params.toString())
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('tableContent').innerHTML = 
                            '<div class="error">Error: ' + data.error + '</div>';
                        return;
                    }
                    
                    renderTable(data);
                    updatePagination(data);
                })
                .catch(error => {
                    document.getElementById('tableContent').innerHTML = 
                        '<div class="error">Error loading data: ' + error + '</div>';
                });
        }
        
        function renderTable(data) {
            if (!data.rows || data.rows.length === 0) {
                document.getElementById('tableContent').innerHTML = 
                    '<div class="loading">No data found</div>';
                return;
            }
            
            let html = '<table><thead><tr>';
            
            // Column headers with search inputs
            data.columns.forEach(column => {
                html += `
                    <th>
                        ${formatColumnName(column)}
                        <input type="text" class="column-search" 
                               placeholder="Search ${formatColumnName(column)}..." 
                               value="${currentFilters[column] || ''}"
                               onkeyup="handleColumnSearch('${column}', this.value)"
                               onclick="event.stopPropagation()">
                    </th>
                `;
            });
            
            html += '</tr></thead><tbody>';
            
            // Data rows
            data.rows.forEach(row => {
                html += '<tr>';
                data.columns.forEach(column => {
                    let value = row[column];
                    if (value === null || value === undefined) {
                        value = '';
                    } else if (typeof value === 'number' && column.toLowerCase().includes('amount')) {
                        value = '$' + value.toFixed(2);
                    }
                    html += `<td>${escapeHtml(String(value))}</td>`;
                });
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            document.getElementById('tableContent').innerHTML = html;
        }
        
        function updatePagination(data) {
            totalPages = data.total_pages;
            currentPage = data.current_page;
            
            document.getElementById('pageInfo').textContent = 
                `Page ${currentPage} of ${totalPages} (${data.total_records.toLocaleString()} total records)`;
            
            document.getElementById('firstBtn').disabled = currentPage <= 1;
            document.getElementById('prevBtn').disabled = currentPage <= 1;
            document.getElementById('nextBtn').disabled = currentPage >= totalPages;
            document.getElementById('lastBtn').disabled = currentPage >= totalPages;
            
            document.getElementById('pagination').style.display = 'flex';
        }
        
        function goToPage(page) {
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            loadTableData();
        }
        
        function searchTable() {
            globalSearchTerm = document.getElementById('globalSearch').value;
            currentPage = 1;
            loadTableData();
        }
        
        function clearSearch() {
            globalSearchTerm = '';
            currentFilters = {};
            currentPage = 1;
            document.getElementById('globalSearch').value = '';
            loadTableData();
        }
        
        function handleColumnSearch(column, value) {
            currentFilters[column] = value;
            currentPage = 1;
            // Debounce the search
            clearTimeout(window.searchTimeout);
            window.searchTimeout = setTimeout(() => {
                loadTableData();
            }, 500);
        }
        
        function formatColumnName(column) {
            return column.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Allow Enter key for global search
        document.getElementById('globalSearch').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchTable();
            }
        });
    </script>
</body>
</html>
"""

def get_db_stats():
    """Get database statistics"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count invoices
            cursor.execute('SELECT COUNT(*) FROM invoices')
            stats['invoices'] = cursor.fetchone()[0]
            
            # Count payments
            cursor.execute('SELECT COUNT(*) FROM payments')
            stats['payments'] = cursor.fetchone()[0]
            
            # Count unpaid invoices
            cursor.execute('SELECT COUNT(*) FROM invoices WHERE status != "PAID"')
            stats['unpaid_invoices'] = cursor.fetchone()[0]
            
            # Count paid invoices
            cursor.execute('SELECT COUNT(*) FROM invoices WHERE status = "PAID"')
            stats['paid_invoices'] = cursor.fetchone()[0]
            
            return stats
    except Exception as e:
        return {'error': str(e)}

def get_table_data(table_name, page=1, page_size=50, global_search='', filters=None):
    """Get paginated table data with search filters"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if filters is None:
                filters = {}
            
            # Define table schemas
            if table_name == 'invoices':
                columns = ['invoice_id', 'contact_name', 'reference', 'amount_due', 'status', 'issue_date', 'due_date']
                base_query = 'SELECT invoice_id, contact_name, reference, amount_due, status, issue_date, due_date FROM invoices'
            elif table_name == 'payments':
                columns = ['payment_id', 'invoice_id', 'amount', 'date', 'reference', 'status']
                base_query = 'SELECT payment_id, invoice_id, amount, date, reference, status FROM payments'
            else:
                return {'error': 'Invalid table name'}
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            # Global search
            if global_search:
                global_conditions = []
                for column in columns:
                    global_conditions.append(f"{column} LIKE ?")
                    params.append(f'%{global_search}%')
                where_conditions.append(f"({' OR '.join(global_conditions)})")
            
            # Column-specific filters
            for column, value in filters.items():
                if value and column in columns:
                    where_conditions.append(f"{column} LIKE ?")
                    params.append(f'%{value}%')
            
            # Construct the final query
            if where_conditions:
                query = f"{base_query} WHERE {' AND '.join(where_conditions)}"
                count_query = f"SELECT COUNT(*) FROM ({query})"
            else:
                query = base_query
                count_query = f"SELECT COUNT(*) FROM {table_name}"
            
            # Get total count
            cursor.execute(count_query, params)
            total_records = cursor.fetchone()[0]
            
            # Calculate pagination
            total_pages = math.ceil(total_records / page_size)
            offset = (page - 1) * page_size
            
            # Get paginated data
            paginated_query = f"{query} ORDER BY {columns[0]} DESC LIMIT ? OFFSET ?"
            cursor.execute(paginated_query, params + [page_size, offset])
            
            rows = [dict(row) for row in cursor.fetchall()]
            
            return {
                'columns': columns,
                'rows': rows,
                'current_page': page,
                'total_pages': total_pages,
                'total_records': total_records,
                'page_size': page_size
            }
            
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    """API endpoint for database statistics"""
    return jsonify(get_db_stats())

@app.route('/api/table')
def api_table():
    """API endpoint for table data with pagination and search"""
    try:
        table = request.args.get('table', 'invoices')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('size', 50))
        global_search = request.args.get('global_search', '')
        
        # Extract column filters
        filters = {}
        for key, value in request.args.items():
            if key.startswith('filter_') and value:
                column = key[7:]  # Remove 'filter_' prefix
                filters[column] = value
        
        return jsonify(get_table_data(table, page, page_size, global_search, filters))
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("🌐 Starting Modern Database Browser...")
    print(f"📊 Database: {DB_PATH}")
    print("🔗 Access at: http://localhost:5001")
    print("💡 Press Ctrl+C to stop")
    print("\n✨ Features:")
    print("  📄 Paginated tables (50 records per page)")
    print("  🔍 Global search across all columns")
    print("  🎯 Individual column search filters")
    print("  📊 Real-time database statistics")
    print("  🔄 Live search with debouncing")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
