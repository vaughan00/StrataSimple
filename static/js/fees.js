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
    
    // Fee type change handler to show/hide relevant fields
    const feeTypeSelect = document.getElementById('fee_type');
    const billingPeriodFields = document.getElementById('billing_period_fields');
    const propertySelectionDiv = document.getElementById('property_selection');
    const feeInfoAlert = document.getElementById('fee_info');
    const periodNameInput = document.getElementById('period_name');
    
    feeTypeSelect.addEventListener('change', function() {
        const selectedType = this.value;
        
        // Show/hide relevant sections based on fee type
        if (selectedType === 'billing_period') {
            billingPeriodFields.style.display = 'block';
            propertySelectionDiv.style.display = 'none';
            feeInfoAlert.innerHTML = '<i class="fas fa-info-circle me-2"></i> The fee per unit will be charged to each property equally.';
            periodNameInput.required = true;
            startDateInput.required = true;
            endDateInput.required = true;
        } else {
            billingPeriodFields.style.display = 'none';
            propertySelectionDiv.style.display = 'block';
            
            if (selectedType === 'opening_balance') {
                feeInfoAlert.innerHTML = '<i class="fas fa-info-circle me-2"></i> Set opening balances for selected properties.';
            } else {
                feeInfoAlert.innerHTML = '<i class="fas fa-info-circle me-2"></i> Ad hoc fees will be applied to selected properties only.';
            }
            
            periodNameInput.required = false;
            startDateInput.required = false;
            endDateInput.required = false;
        }
    });
    
    // Initialize fee tables for each billing period
    const feeTableContainers = document.querySelectorAll('.fees-table-container');
    
    feeTableContainers.forEach(container => {
        const periodId = container.getAttribute('data-period-id');
        const tableBodyId = `feesTable${periodId}Body`;
        
        // Get the table body element
        const tableBody = document.getElementById(tableBodyId);
        
        // Fetch fees data for this period
        fetch(`/api/billing_periods/${periodId}/fees`)
            .then(response => response.json())
            .then(data => {
                // Clear loading spinner
                tableBody.innerHTML = '';
                
                // If no fees found
                if (data.length === 0) {
                    const emptyRow = document.createElement('tr');
                    emptyRow.innerHTML = `
                        <td colspan="7" class="text-center">
                            <div class="alert alert-info">No fees found for this period.</div>
                        </td>
                    `;
                    tableBody.appendChild(emptyRow);
                    return;
                }
                
                // Populate table with data
                data.forEach(fee => {
                    const row = document.createElement('tr');
                    
                    // Calculate the payment status and amount
                    const payments = fee.payments || [];
                    const totalPaid = payments.reduce((sum, payment) => sum + payment.amount, 0);
                    const remaining = fee.amount - totalPaid;
                    const paymentStatus = fee.paid ? 'paid' : (totalPaid > 0 ? 'partial' : 'unpaid');
                    
                    // Create status badge
                    let statusBadge;
                    if (totalPaid >= fee.amount) {
                        statusBadge = '<span class="badge bg-success">Paid ✅</span>';
                    } else if (totalPaid > 0) {
                        statusBadge = '<span class="badge bg-warning text-dark">Partial 🟠</span>';
                    } else {
                        statusBadge = '<span class="badge bg-danger">Unpaid 🔴</span>';
                    }
                    
                    // Create action button
                    const actionButton = !fee.paid ? 
                        `<button class="btn btn-sm btn-success mark-paid-btn" data-fee-id="${fee.id}">
                            <i class="fas fa-check me-1"></i>Mark Paid
                        </button>` : '';
                    
                    // Format fee type for display
                    let feeTypeBadge = '';
                    if (fee.fee_type === 'billing_period') {
                        feeTypeBadge = '<span class="badge bg-primary">Billing Period</span>';
                    } else if (fee.fee_type === 'opening_balance') {
                        feeTypeBadge = '<span class="badge bg-secondary">Opening Balance</span>';
                    } else if (fee.fee_type === 'ad_hoc') {
                        feeTypeBadge = '<span class="badge bg-info">Ad Hoc</span>';
                    } else {
                        feeTypeBadge = '<span class="badge bg-primary">Billing Period</span>';
                    }
                    
                    // Set row HTML
                    row.innerHTML = `
                        <td>${fee.unit_number}</td>
                        <td>${fee.owner_name || 'Unknown'}</td>
                        <td>$${fee.amount.toFixed(2)}</td>
                        <td>${remaining > 0 ? 
                            `<span class="text-danger">$${remaining.toFixed(2)}</span>` : 
                            `<span class="text-success">$0.00</span>`}
                        </td>
                        <td>${feeTypeBadge}</td>
                        <td>${statusBadge}</td>
                        <td>${actionButton}</td>
                    `;
                    
                    // Add row to table
                    tableBody.appendChild(row);
                });
                
                // Add event listeners to the mark paid buttons
                const markPaidButtons = tableBody.querySelectorAll('.mark-paid-btn');
                markPaidButtons.forEach(button => {
                    button.addEventListener('click', function() {
                        const feeId = this.getAttribute('data-fee-id');
                        const row = this.closest('tr');
                        markFeePaid(feeId, row);
                    });
                });
            })
            .catch(error => {
                console.error(`Error fetching fees for period ${periodId}:`, error);
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center">
                            <div class="alert alert-danger">Error loading fees.</div>
                        </td>
                    </tr>
                `;
            });
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
                // Update the row cells for remaining amount, status and action
                const remainingCell = row.cells[3];
                const statusCell = row.cells[4];
                const actionCell = row.cells[5];
                
                remainingCell.innerHTML = '<span class="text-success">$0.00</span>';
                statusCell.innerHTML = '<span class="badge bg-success">Paid ✅</span>';
                actionCell.innerHTML = ''; // Remove the mark paid button
                
                // Show success message
                alert('Fee has been marked as paid.');
            }
        })
        .catch(error => console.error('Error marking fee as paid:', error));
    }
});
