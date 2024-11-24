<script>
    let ws;

    // Initialize WebSocket and set up events
    function initWebSocket() {
        ws = new WebSocket('ws://localhost:8765'); // Change to server IP if needed

        ws.onopen = function() {
            console.log('Connected to WebSocket server');
            document.getElementById('slotStatus').innerText = "Connected to server.";
        };

        // Handle messages from the server
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);

            if (message.type === 'parkingStatus') {
                document.getElementById('slotStatus').innerText = `Slot ${message.slot}: ${message.status}`;
            } else if (message.type === 'rfidStatus') {
                document.getElementById('rfidMessage').innerText = message.message;
            } else if (message.type === 'bookingConfirmation') {
                document.getElementById('slotStatus').innerText = `Booking confirmed for Slot ${message.slot} from ${message.startTime} to ${message.endTime}. Total Cost: $${message.cost}`;
            } else if (message.type === 'availabilityStatus') {
                document.getElementById('slotStatus').innerText = `Slot ${message.slot} is ${message.status}.`;
            } else if (message.type === 'error') {
                console.error("Error from server:", message.message);
                document.getElementById('slotStatus').innerText = `Error: ${message.message}`;
            }
        };

        ws.onclose = function() {
            console.log('Disconnected from WebSocket server');
            document.getElementById('slotStatus').innerText = "Disconnected from server. Attempting to reconnect...";
            setTimeout(() => {
                document.getElementById('slotStatus').innerText = "Reconnecting...";
                reconnectWebSocket();
            }, 3000);
        };

        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    }

    function reconnectWebSocket() {
        if (ws.readyState !== WebSocket.OPEN && ws.readyState !== WebSocket.CONNECTING) {
            initWebSocket();
        }
    }

    // Send WebSocket message with connection check
    function sendWebSocketMessage(data) {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocket is not open. Message not sent:', data);
            document.getElementById('slotStatus').innerText = "Unable to send message. WebSocket not connected.";
        }
    }

    // Check slot availability
    function checkAvailability() {
        const slot = document.getElementById('slot').value;
        sendWebSocketMessage({ type: 'checkAvailability', slot: slot });
    }

    // Calculate estimated cost
    function calculateCost() {
        const startTime = document.getElementById('startTime').value;
        const endTime = document.getElementById('endTime').value;

        if (startTime && endTime) {
            const durationHours = (new Date(endTime) - new Date(startTime)) / 3600000;
            const hourlyRate = 5.0; // Replace with actual hourly rate
            const estimatedCost = (durationHours * hourlyRate).toFixed(2);

            document.getElementById('costEstimate').innerText = `Estimated Cost: $${estimatedCost}`;
        }
    }

    // Submit booking request
    function submitBooking(event) {
        event.preventDefault();
        const slot = document.getElementById('slot').value;
        const startTime = document.getElementById('startTime').value;
        const endTime = document.getElementById('endTime').value;

        const bookingData = {
            type: 'booking',
            slot: slot,
            startTime: startTime,
            endTime: endTime
        };

        sendWebSocketMessage(bookingData);
        document.getElementById('slotStatus').innerText = "Booking submitted. Waiting for confirmation...";
    }

    // Request RFID scan
    function requestRFIDScan() {
        const rfidRequest = { type: 'rfidScanRequest' };
        sendWebSocketMessage(rfidRequest);
        document.getElementById('rfidMessage').innerText = "Please scan your RFID card...";
    }

    // Update parking slot status
    function updateParkingStatus(slot, status) {
        const statusUpdate = {
            type: 'update_status',
            slot: slot,
            status: status
        };

        sendWebSocketMessage(statusUpdate);
        document.getElementById('slotStatus').innerText = `Updating status for Slot ${slot} to ${status}...`;
    }

    // Initialize WebSocket on page load
    window.onload = function() {
        initWebSocket();
    };
</script>
