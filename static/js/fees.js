document.addEventListener('DOMContentLoaded', function() {
    // Set default dates for the new billing period form
    const today = new Date();
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    // Set start date to today
    startDateInput.valueAsDate = today;
    
    // Set end date to 3 months from today
    const endDate = new Date(today);
    endDate.setMonth(endDate.getMonth() + 3);
    endDateInput.valueAsDate = endDate;
    
    // Initialize fee tables for each billing period
    const feeTableContainers = document.querySelectorAll('.fees-table-container');
    
    feeTableContainers.forEach(container => {
        const periodId = container.getAttribute('data-period-id');
        const tableId = `feesTable${periodId}`;
        
        // Fetch fees data for this period
        fetch(`/api/billing_periods/${periodId}/fees`)
            .then(response => response.json())
            .then(data => {
                // Initialize Tabulator
                const table = new Tabulator(`#${tableId}`, {
                    data: data,
                    layout: "fitColumns",
                    pagination: "local",
                    paginationSize: 5,
                    columns: [
                        {title: "Unit", field: "unit_number", sorter: "string"},
                        {title: "Owner", field: "owner_name", sorter: "string"},
                        {
                            title: "Amount", 
                            field: "amount", 
                            sorter: "number",
                            formatter: function(cell) {
                                return '$' + cell.getValue().toFixed(2);
                            }
                        },
                        {
                            title: "Status", 
                            field: "paid", 
                            formatter: function(cell) {
                                const value = cell.getValue();
                                return value ? 
                                    '<span class="badge bg-success">Paid</span>' : 
                                    '<span class="badge bg-warning">Pending</span>';
                            }
                        },
                        {
                            title: "Actions",
                            formatter: function(cell) {
                                const rowData = cell.getRow().getData();
                                if (!rowData.paid) {
                                    return `<button class="btn btn-sm btn-success mark-paid-btn" data-fee-id="${rowData.id}">
                                        <i class="fas fa-check me-1"></i>Mark Paid
                                    </button>`;
                                }
                                return '';
                            },
                            cellClick: function(e, cell) {
                                // Handle mark as paid button click
                                if (e.target.classList.contains('mark-paid-btn') || 
                                    e.target.parentElement.classList.contains('mark-paid-btn')) {
                                    const feeId = e.target.getAttribute('data-fee-id') || 
                                                e.target.parentElement.getAttribute('data-fee-id');
                                    markFeePaid(feeId, cell.getRow());
                                }
                            }
                        }
                    ]
                });
                
                // Function to mark a fee as paid
                function markFeePaid(feeId, row) {
                    fetch(`/api/mark_fee_paid/${feeId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Update the row data
                            const rowData = row.getData();
                            rowData.paid = true;
                            row.update(rowData);
                            
                            // Show success message
                            alert('Fee has been marked as paid.');
                        }
                    })
                    .catch(error => console.error('Error marking fee as paid:', error));
                }
            })
            .catch(error => console.error(`Error fetching fees for period ${periodId}:`, error));
    });
});
