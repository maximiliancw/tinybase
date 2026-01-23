<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .button:hover { background-color: #0056b3; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome to {{ instance_name }}!</h2>
        <p>Your account has been successfully created.</p>
        <p>You can now log in to your account using the email address: <strong>{{ email }}</strong></p>
        {% if login_url %}
        <p>Click the button below to access your account:</p>
        <a href="{{ login_url }}" class="button">Log In</a>
        {% endif %}
        <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>
        <div class="footer">
            <p>This is an automated message from {{ instance_name }}.</p>
        </div>
    </div>
</body>
</html>