function initCharts(stats) {
    // Set default font color for all charts
    Chart.defaults.color = '#333';

    // Distribution des utilisateurs par OU
    const ouChart = document.getElementById('ouDistributionChart');
    if (stats.users && stats.users.ou_distribution && ouChart) {
        const ouLabels = Object.keys(stats.users.ou_distribution);
        const ouData = Object.values(stats.users.ou_distribution);
        
        new Chart(ouChart, {
            type: 'pie',
            data: {
                labels: ouLabels,
                datasets: [{
                    data: ouData,
                    backgroundColor: generateColors(ouData.length)
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    title: {
                        display: false
                    }
                }
            }
        });
    }

    // Top 10 des groupes
    const groupsChart = document.getElementById('topGroupsChart');
    if (stats.groups && stats.groups.top_groups && groupsChart) {
        const groupLabels = stats.groups.top_groups.map(g => g[0]);
        const groupData = stats.groups.top_groups.map(g => g[1]);
        
        new Chart(groupsChart, {
            type: 'bar',
            data: {
                labels: groupLabels,
                datasets: [{
                    label: 'Nombre de membres',
                    data: groupData,
                    backgroundColor: '#4e73df',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Distribution des administrateurs par OU
    const adminChart = document.getElementById('adminOuChart');
    if (stats.security && stats.security.admin_ou_distribution && adminChart) {
        const adminOuLabels = Object.keys(stats.security.admin_ou_distribution);
        const adminOuData = Object.values(stats.security.admin_ou_distribution);
        
        new Chart(adminChart, {
            type: 'doughnut',
            data: {
                labels: adminOuLabels,
                datasets: [{
                    data: adminOuData,
                    backgroundColor: generateColors(adminOuData.length)
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
}

// Fonction pour générer des couleurs aléatoires
function generateColors(count) {
    const baseColors = [
        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
        '#858796', '#5a5c69', '#2e59d9', '#17a673', '#2c9faf'
    ];
    
    // Si on a besoin de plus de couleurs que dans notre palette de base
    if (count > baseColors.length) {
        const extraColors = [];
        for (let i = 0; i < count - baseColors.length; i++) {
            const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
            extraColors.push(color);
        }
        return [...baseColors, ...extraColors];
    }
    
    return baseColors.slice(0, count);
}
