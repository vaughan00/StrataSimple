document.addEventListener('DOMContentLoaded', function() {
    // Define global variables for unmatched payments
    let unmatchedPayments = [];
    
    if (document.getElementById('unmatched-table')) {
        // Extract unmatched payments from the table
        const rows = document.querySelectorAll('#unmatched-table tbody tr');
        rows.forEach((row, index) => {
            const cells = row.querySelectorAll('td');
            unmatchedPayments.push({
                index: index,
                date: cells[0].textContent,
                amount: parseFloat(cells[1].textContent.replace('$', '')),
                description: cells[2].textContent,
                reference: cells[3].textContent
            });
        });
        
        // Set up event listeners for manual match buttons
        const matchButtons = document.querySelectorAll('.manual-match-btn');
        matchButtons.forEach(button => {
            button.addEventListener('click', function() {
                const paymentIndex = this.getAttribute('data-payment-index');
                showMatchModal(paymentIndex);
            });
        });
        
        // Fetch properties for the dropdown
        fetch('/api/properties')
            .then(response => response.json())
            .then(data => {
                const propertySelect = document.getElementById('property-select');
                
                // Clear existing options
                propertySelect.innerHTML = '<option value="" selected disabled>Choose a property...</option>';
                
                // Add options for each property
                data.forEach(property => {
                    const option = document.createElement('option');
                    option.value = property.id;
                    option.textContent = `Unit ${property.unit_number} - ${property.owner_name}`;
                    propertySelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error fetching properties:', error));
        
        // Set up event listener for confirm match button
        document.getElementById('confirm-match-btn').addEventListener('click', function() {
            const paymentIndex = document.getElementById('payment-index').value;
            const propertyId = document.getElementById('property-select').value;
            
            if (!propertyId) {
                alert('Please select a property');
                return;
            }
            
            // Send request to match payment to property
            const payment = unmatchedPayments[paymentIndex];
            
            // Here you would normally send an AJAX request to save this match
            // For demo purposes, we'll just show a success message and reload
            alert(`Payment of $${payment.amount.toFixed(2)} successfully matched to property ID ${propertyId}`);
            
            // Reload page to reflect changes
            window.location.reload();
        });
    }
    
    // Function to show match modal with payment details
    function showMatchModal(paymentIndex) {
        const payment = unmatchedPayments[paymentIndex];
        
        // Set hidden input value
        document.getElementById('payment-index').value = paymentIndex;
        
        // Set payment details in modal
        document.getElementById('modal-payment-date').textContent = payment.date;
        document.getElementById('modal-payment-amount').textContent = '$' + payment.amount.toFixed(2);
        document.getElementById('modal-payment-reference').textContent = payment.reference;
        document.getElementById('modal-payment-description').textContent = payment.description;
    }
});
