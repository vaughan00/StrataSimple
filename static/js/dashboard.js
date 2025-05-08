document.addEventListener('DOMContentLoaded', function() {
    // Fetch properties data for table and charts
    fetch('/api/properties')
        .then(response => response.json())
        .then(data => {
            initializePropertiesTable(data);
            initializeBalancesChart(data);
            initializeFeesVsPaymentsChart(data);
        })
        .catch(error => console.error('Error fetching properties data:', error));
    
    // Initialize Properties Table with Tabulator
    function initializePropertiesTable(data) {
        new Tabulator("#propertiesTable", {
            data: data,
            layout: "fitColumns",
            responsiveLayout: "collapse",
            pagination: "local",
            paginationSize: 10,
            columns: [
                {title: "Unit", field: "unit_number", sorter: "string", headerFilter: true},
                {title: "Owner", field: "owner_name", sorter: "string", headerFilter: true},
                {
                    title: "Balance", 
                    field: "balance", 
                    sorter: "number",
                    formatter: function(cell) {
                        const value = cell.getValue();
                        const formattedValue = '$' + value.toFixed(2);
                        return `<span class="${value < 0 ? 'text-danger' : 'text-success'}">${formattedValue}</span>`;
                    }
                },
                {
                    title: "Unpaid Fees", 
                    field: "unpaid_fees", 
                    sorter: "number",
                    formatter: function(cell) {
                        const value = cell.getValue();
                        return value > 0 ? `<span class="text-danger">$${value.toFixed(2)}</span>` : '$0.00';
                    }
                },
                {
                    title: "Total Payments", 
                    field: "total_payments", 
                    sorter: "number",
                    formatter: function(cell) {
                        return '$' + cell.getValue().toFixed(2);
                    }
                }
            ]
        });
    }
    
    // Initialize Balances Chart
    function initializeBalancesChart(data) {
        const ctx = document.getElementById('balancesChart').getContext('2d');
        
        // Extract data for chart
        const unitNumbers = data.map(property => 'Unit ' + property.unit_number);
        const balances = data.map(property => property.balance);
        
        // Create color array (red for negative, green for positive)
        const backgroundColors = balances.map(balance => 
            balance < 0 ? 'rgba(220, 53, 69, 0.7)' : 'rgba(40, 167, 69, 0.7)'
        );
        
        // Create chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: unitNumbers,
                datasets: [{
                    label: 'Current Balance',
                    data: balances,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '$' + context.raw.toFixed(2);
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Initialize Fees vs Payments Chart
    function initializeFeesVsPaymentsChart(data) {
        const ctx = document.getElementById('feesVsPaymentsChart').getContext('2d');
        
        // Calculate totals
        const totalFees = data.reduce((sum, property) => sum + property.unpaid_fees, 0);
        const totalPayments = data.reduce((sum, property) => sum + property.total_payments, 0);
        
        // Create chart
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Total Paid', 'Outstanding Fees'],
                datasets: [{
                    data: [totalPayments, totalFees],
                    backgroundColor: ['rgba(40, 167, 69, 0.7)', 'rgba(220, 53, 69, 0.7)'],
                    borderColor: ['rgba(40, 167, 69, 1)', 'rgba(220, 53, 69, 1)'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: $${value.toFixed(2)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
});
