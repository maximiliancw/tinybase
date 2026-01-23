<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; }
        .section { margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 4px; }
        .section h3 { margin-top: 0; color: #007bff; }
        .metric { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #dee2e6; }
        .metric:last-child { border-bottom: none; }
        .metric-label { font-weight: 600; }
        .metric-value { color: #007bff; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background-color: #007bff; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ instance_name }} - Admin Report</h1>
            <p>Report generated on {{ report_date }}</p>
        </div>

        {% if summary %}
        <div class="section">
            <h3>Summary</h3>
            {% for key, value in summary.items() %}
            <div class="metric">
                <span class="metric-label">{{ key }}:</span>
                <span class="metric-value">{{ value }}</span>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if collections %}
        <div class="section">
            <h3>Collection Statistics</h3>
            <table>
                <thead>
                    <tr>
                        <th>Collection</th>
                        <th>Record Count</th>
                    </tr>
                </thead>
                <tbody>
                    {% for collection, count in collections.items() %}
                    <tr>
                        <td>{{ collection }}</td>
                        <td>{{ count }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if functions %}
        <div class="section">
            <h3>Function Statistics</h3>
            <table>
                <thead>
                    <tr>
                        <th>Function</th>
                        <th>Total Calls</th>
                        <th>Success Rate</th>
                        <th>Avg Duration (ms)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for func_name, stats in functions.items() %}
                    <tr>
                        <td>{{ func_name }}</td>
                        <td>{{ stats.total_calls }}</td>
                        <td>{{ "%.1f"|format(stats.success_rate * 100) }}%</td>
                        <td>{{ "%.0f"|format(stats.avg_duration_ms) if stats.avg_duration_ms else "N/A" }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if users %}
        <div class="section">
            <h3>User Statistics</h3>
            <div class="metric">
                <span class="metric-label">Total Users:</span>
                <span class="metric-value">{{ users.total }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Admin Users:</span>
                <span class="metric-value">{{ users.admins }}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Regular Users:</span>
                <span class="metric-value">{{ users.regular }}</span>
            </div>
        </div>
        {% endif %}

        {% if notes %}
        <div class="section">
            <h3>Notes</h3>
            <p>{{ notes }}</p>
        </div>
        {% endif %}

        <div class="footer">
            <p>This is an automated report from {{ instance_name }}.</p>
            <p>For more details, please log in to the admin interface.</p>
        </div>
    </div>
</body>
</html>