let invoices = [];
const ws = new WebSocket('ws://192.168.1.10:8765'); // Replace with the actual WebSocket server IP

ws.onopen = function() {
    console.log('Connected to WebSocket server for invoice management');
    fetchInvoices(); // Fetch initial invoice data on connection
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);

    if (message.type === 'invoiceList') {
        invoices = message.invoices;
        renderInvoices(); // Render the fetched invoice list
    } else if (message.type === 'invoiceAdded') {
        invoices.push(message.invoice);
        renderInvoices();
    } else if (message.type === 'invoiceUpdated') {
        const index = invoices.findIndex(inv => inv.invoiceId === message.invoice.invoiceId);
        if (index !== -1) {
            invoices[index] = message.invoice;
            renderInvoices();
        }
    } else if (message.type === 'invoiceDeleted') {
        invoices = invoices.filter(inv => inv.invoiceId !== message.invoiceId);
        renderInvoices();
    }
};

ws.onclose = function() {
    console.log('Disconnected from WebSocket server');
};

// Fetch the initial list of invoices from the server
function fetchInvoices() {
    const request = JSON.stringify({ type: 'getInvoices' });
    ws.send(request);
}

// Add a new invoice
function addInvoice() {
    const invoiceId = document.getElementById('invoiceId').value;
    const customerName = document.getElementById('customerName').value;
    const amount = document.getElementById('amount').value;

    if (!invoiceId || !customerName || !amount) {
        alert("Vui lòng điền đầy đủ thông tin.");
        return;
    }

    const newInvoice = { invoiceId, customerName, amount };

    // Send the new invoice to the server
    ws.send(JSON.stringify({
        type: 'addInvoice',
        invoice: newInvoice
    }));

    clearForm();
}

// Display the invoice list in the table
function renderInvoices() {
    const invoiceTable = document.getElementById('invoiceTable').getElementsByTagName('tbody')[0];
    invoiceTable.innerHTML = ''; // Clear old content

    invoices.forEach((invoice, index) => {
        const row = invoiceTable.insertRow();
        
        row.insertCell(0).innerText = invoice.invoiceId;
        row.insertCell(1).innerText = invoice.customerName;
        row.insertCell(2).innerText = invoice.amount;

        // Create edit and delete buttons
        const actionCell = row.insertCell(3);
        actionCell.innerHTML = `
            <button onclick="editInvoice(${index})">Sửa</button>
            <button onclick="deleteInvoice(${index})">Xóa</button>
        `;
    });
}

// Delete an invoice
function deleteInvoice(index) {
    const invoiceId = invoices[index].invoiceId;

    // Send delete request to the server
    ws.send(JSON.stringify({
        type: 'removeInvoice',
        invoiceId: invoiceId
    }));
}

// Edit an invoice
function editInvoice(index) {
    const invoice = invoices[index];
    document.getElementById('invoiceId').value = invoice.invoiceId;
    document.getElementById('customerName').value = invoice.customerName;
    document.getElementById('amount').value = invoice.amount;

    // Change the "Add" button to a "Save" button
    const submitButton = document.querySelector('#invoiceForm button');
    submitButton.textContent = 'Lưu thay đổi';
    submitButton.onclick = function () {
        saveInvoice(index);
    };
}

// Save changes to an edited invoice
function saveInvoice(index) {
    const updatedInvoice = {
        invoiceId: document.getElementById('invoiceId').value,
        customerName: document.getElementById('customerName').value,
        amount: document.getElementById('amount').value
    };

    // Update the invoice in the local array
    invoices[index] = updatedInvoice;

    // Send the updated invoice to the server
    ws.send(JSON.stringify({
        type: 'updateInvoice',
        invoice: updatedInvoice
    }));

    clearForm();

    // Change the "Save" button back to "Add"
    const submitButton = document.querySelector('#invoiceForm button');
    submitButton.textContent = 'Thêm hóa đơn';
    submitButton.onclick = addInvoice;
}

// Clear the input fields after completing an action
function clearForm() {
    document.getElementById('invoiceId').value = '';
    document.getElementById('customerName').value = '';
    document.getElementById('amount').value = '';
}
