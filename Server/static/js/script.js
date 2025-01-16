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

    fetch('/api/all')
        .then(handleResponse)
        .then(data => {
            document.getElementById('current-time').textContent = data['Current Time'];
            document.getElementById('ip-address').textContent = data['IP Address'];
            document.getElementById('cpu-usage').textContent = data['CPU Usage'];
            document.getElementById('soc-temp').textContent = data['SoC Temperature'];
            document.getElementById('total-ram').textContent = data['Total RAM'];
            document.getElementById('used-ram').textContent = data['Used RAM'];
            document.getElementById('total-swap').textContent = data['Total Swap'];
            document.getElementById('used-swap').textContent = data['Used Swap'];
        })
        .catch(error => console.error('Error fetching API data:', error));
    
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
