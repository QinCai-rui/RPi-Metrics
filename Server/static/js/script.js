window.onload = function() {
    const handleResponse = (response) => {
        if (response.status === 401) {
            alert('Wrong API key');
            throw new Error('Unauthorized');
        } else if (response.status === 429) {
            alert('Too many requests, please try again later.');
            throw new Error('Too Many Requests');
        }
        return response.json();
    };

    // Function to fetch and update data
    const updateData = () => {
        fetch('/api/all')
            .then(handleResponse)
            .then(data => {
                // Original metrics
                document.getElementById('current-time').textContent = data['Current Time'];
                document.getElementById('ip-address').textContent = data['IP Address'].replaceAll(" ", "\n");
                document.getElementById('cpu-usage').textContent = data['CPU Usage'];
                document.getElementById('soc-temp').textContent = data['SoC Temperature'].replace("C", "°C");
                document.getElementById('total-ram').textContent = data['Total RAM'];
                document.getElementById('used-ram').textContent = data['Used RAM'].concat("MiB");
                document.getElementById('total-swap').textContent = data['Total Swap'];
                document.getElementById('used-swap').textContent = data['Used Swap'].concat("MiB");
                
                // New metrics
                document.getElementById('system-uptime').textContent = data['System Uptime'];
                document.getElementById('disk-usage').textContent = data['Disk Usage'];
                document.getElementById('disk-total').textContent = data['Disk Total'];
                document.getElementById('disk-used').textContent = data['Disk Used'];
                document.getElementById('disk-available').textContent = data['Disk Available'];
                document.getElementById('system-model').textContent = data['System Model'];
                document.getElementById('kernel-version').textContent = data['Kernel Version'];
                document.getElementById('os-version').textContent = data['OS'];
            })
            .catch(error => console.error('Error fetching API data:', error));
    };

    // Initial data load
    updateData();
    
    // Update data every 5 seconds
    setInterval(updateData, 5000);
    
    // Shutdown button handler
    document.getElementById('shutdown-btn').addEventListener('click', function() {
        const apiKey = prompt('Please enter your API key:');
        if (apiKey && confirm('Are you sure you want to shut down the system?')) {
            fetch('/api/shutdown', {
                method: 'POST',
                headers: {
                    'x-api-key': apiKey
                }
            })
            .then(handleResponse)
            .then(data => alert(data.message))
            .catch(error => console.error('Error during shutdown:', error));
        }
    });

    // Reboot button handler
    document.getElementById('reboot-btn').addEventListener('click', function() {
        const apiKey = prompt('Please enter your API key:');
        if (apiKey && confirm('Are you sure you want to reboot the system?')) {
            fetch('/api/reboot', {
                method: 'POST',
                headers: {
                    'x-api-key': apiKey
                }
            })
            .then(handleResponse)
            .then(data => alert(data.message))
            .catch(error => console.error('Error during reboot:', error));
        }
    });

    // Update button handler
    document.getElementById('update-btn').addEventListener('click', function() {
        const apiKey = prompt('Please enter your API key:');
        if (apiKey && confirm('Are you sure you want to update the system?')) {
            alert('This might take some time. Please hold on!');
            fetch('/api/update', {
                method: 'POST',
                headers: {
                    'x-api-key': apiKey
                }
            })
            .then(handleResponse)
            .then(data => alert(data.message))
            .catch(error => console.error('Error during update:', error));
        }
    });    
};
