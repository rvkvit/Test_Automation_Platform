/**
 * Analytics JavaScript for Test Automation Platform
 * Handles chart rendering and data visualization
 */

window.Analytics = {
    charts: {},
    
    /**
     * Initialize analytics with data
     */
    init: function(data, projectId, days) {
        this.data = data;
        this.projectId = projectId;
        this.days = days;
        
        if (data && data.trends) {
            this.renderTrendChart();
            this.renderPieChart();
            
            if (data.duration_trends) {
                this.renderDurationChart();
            }
        }
    },
    
    /**
     * Render pass/fail trend chart
     */
    renderTrendChart: function() {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;
        
        const trends = this.data.trends;
        const labels = trends.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        
        // Destroy existing chart if it exists
        if (this.charts.trend) {
            this.charts.trend.destroy();
        }
        
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Passed',
                        data: trends.map(item => item.passed),
                        backgroundColor: 'rgba(25, 135, 84, 0.2)',
                        borderColor: 'rgba(25, 135, 84, 1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Failed',
                        data: trends.map(item => item.failed),
                        backgroundColor: 'rgba(220, 53, 69, 0.2)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Pass Rate (%)',
                        data: trends.map(item => item.pass_rate),
                        backgroundColor: 'rgba(13, 202, 240, 0.2)',
                        borderColor: 'rgba(13, 202, 240, 1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Test Execution Trends'
                    },
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                if (context.datasetIndex === 2) {
                                    return '';
                                }
                                const dataIndex = context.dataIndex;
                                const total = trends[dataIndex].total;
                                return `Total: ${total}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Number of Tests'
                        },
                        beginAtZero: true
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Pass Rate (%)'
                        },
                        min: 0,
                        max: 100,
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    },
    
    /**
     * Render pie chart for overall results
     */
    renderPieChart: function() {
        const ctx = document.getElementById('pieChart');
        if (!ctx) return;
        
        const trends = this.data.trends;
        const totalPassed = trends.reduce((sum, item) => sum + item.passed, 0);
        const totalFailed = trends.reduce((sum, item) => sum + item.failed, 0);
        const total = totalPassed + totalFailed;
        
        if (total === 0) {
            ctx.parentNode.innerHTML = '<div class="text-center py-5 text-muted">No execution data available</div>';
            return;
        }
        
        // Destroy existing chart if it exists
        if (this.charts.pie) {
            this.charts.pie.destroy();
        }
        
        this.charts.pie = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Passed', 'Failed'],
                datasets: [{
                    data: [totalPassed, totalFailed],
                    backgroundColor: [
                        'rgba(25, 135, 84, 0.8)',
                        'rgba(220, 53, 69, 0.8)'
                    ],
                    borderColor: [
                        'rgba(25, 135, 84, 1)',
                        'rgba(220, 53, 69, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Overall Results (${this.days} days)`
                    },
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    },
    
    /**
     * Render duration trend chart
     */
    renderDurationChart: function() {
        const ctx = document.getElementById('durationChart');
        if (!ctx) return;
        
        const durationData = this.data.duration_trends;
        const labels = durationData.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        
        // Destroy existing chart if it exists
        if (this.charts.duration) {
            this.charts.duration.destroy();
        }
        
        this.charts.duration = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Average Duration (seconds)',
                    data: durationData.map(item => item.avg_duration),
                    backgroundColor: 'rgba(255, 193, 7, 0.6)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Average Execution Duration'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const seconds = context.parsed.y;
                                const formatted = TestApp.utils.formatDuration(seconds);
                                return `Duration: ${formatted}`;
                            },
                            afterLabel: function(context) {
                                const dataIndex = context.dataIndex;
                                const execCount = durationData[dataIndex].execution_count;
                                return `Executions: ${execCount}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Duration (seconds)'
                        },
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return TestApp.utils.formatDuration(value);
                            }
                        }
                    }
                }
            }
        });
    },
    
    /**
     * Update charts with new data
     */
    updateCharts: function(newData) {
        this.data = newData;
        
        if (newData && newData.trends) {
            this.renderTrendChart();
            this.renderPieChart();
            
            if (newData.duration_trends) {
                this.renderDurationChart();
            }
        }
    },
    
    /**
     * Destroy all charts
     */
    destroyCharts: function() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    },
    
    /**
     * Export chart as image
     */
    exportChart: function(chartName) {
        const chart = this.charts[chartName];
        if (!chart) return;
        
        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = `${chartName}-chart.png`;
        link.href = url;
        link.click();
    },
    
    /**
     * Toggle chart animation
     */
    toggleAnimation: function(enabled) {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.options.animation = enabled;
                chart.update();
            }
        });
    }
};

// Initialize analytics function (called from template)
function initializeAnalytics(data, projectId, days) {
    Analytics.init(data, projectId, days);
}

// Real-time updates for analytics
Analytics.RealTimeUpdater = {
    interval: null,
    isRunning: false,
    
    start: function(updateInterval = 30000) {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.interval = setInterval(() => {
            this.fetchAndUpdate();
        }, updateInterval);
    },
    
    stop: function() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        this.isRunning = false;
    },
    
    fetchAndUpdate: function() {
        const params = new URLSearchParams();
        if (Analytics.projectId) {
            params.set('project_id', Analytics.projectId);
        }
        params.set('days', Analytics.days);
        
        fetch(`/analytics/api/dashboard-metrics?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.updateDashboardMetrics(data.metrics);
                }
            })
            .catch(error => {
                console.warn('Failed to fetch analytics updates:', error);
            });
    },
    
    updateDashboardMetrics: function(metrics) {
        // Update summary cards
        const elements = {
            'total-executions': metrics.total_executions,
            'pass-rate': metrics.pass_rate_7_days + '%',
            'total-projects': metrics.total_projects,
            'total-scripts': metrics.total_scripts
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
        
        // Update recent executions table if present
        this.updateRecentExecutions(metrics.recent_executions);
    },
    
    updateRecentExecutions: function(executions) {
        const tbody = document.querySelector('#recent-executions tbody');
        if (!tbody || !executions) return;
        
        tbody.innerHTML = executions.map(execution => `
            <tr>
                <td>${execution.project_name}</td>
                <td>${execution.script_name || '<em>Suite Run</em>'}</td>
                <td>
                    <span class="badge bg-${execution.status === 'passed' ? 'success' : execution.status === 'failed' ? 'danger' : 'warning'}">
                        ${execution.status.charAt(0).toUpperCase() + execution.status.slice(1)}
                    </span>
                </td>
                <td>${execution.duration ? execution.duration.toFixed(1) + 's' : '-'}</td>
                <td>${new Date(execution.started_at).toLocaleString()}</td>
            </tr>
        `).join('');
    }
};

// Chart theme configuration
Analytics.themes = {
    dark: {
        backgroundColor: 'rgba(248, 249, 250, 0.1)',
        gridColor: 'rgba(248, 249, 250, 0.1)',
        textColor: '#f8f9fa'
    },
    light: {
        backgroundColor: 'rgba(0, 0, 0, 0.1)',
        gridColor: 'rgba(0, 0, 0, 0.1)',
        textColor: '#212529'
    }
};

// Apply theme to charts
Analytics.applyTheme = function(themeName) {
    const theme = this.themes[themeName];
    if (!theme) return;
    
    Chart.defaults.color = theme.textColor;
    Chart.defaults.backgroundColor = theme.backgroundColor;
    Chart.defaults.borderColor = theme.gridColor;
    Chart.defaults.scale.grid.color = theme.gridColor;
    
    // Update existing charts
    Object.values(this.charts).forEach(chart => {
        if (chart) chart.update();
    });
};

// Detect and apply theme
document.addEventListener('DOMContentLoaded', function() {
    const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    Analytics.applyTheme(isDarkTheme ? 'dark' : 'light');
});

// Handle theme changes
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
            const isDarkTheme = mutation.target.getAttribute('data-bs-theme') === 'dark';
            Analytics.applyTheme(isDarkTheme ? 'dark' : 'light');
        }
    });
});

observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-bs-theme']
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    Analytics.RealTimeUpdater.stop();
    Analytics.destroyCharts();
});
