// JS created with help from Microsoft Copilot
window.onload = function() {
    fetch('/api/all')
        .then(response => response.json())
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
};
