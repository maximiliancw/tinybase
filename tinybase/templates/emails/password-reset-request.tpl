<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .button:hover { background-color: #0056b3; }
        hr { margin: 30px 0; }
        footer { padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Reset Request</h2>
        <p>You requested to reset your password for your {{ instance_name }} account.</p>
        <p>Click the button below to reset your password:<br/>
            <a href="{{ reset_url }}" class="button">Reset Password</a>
        </p>
        <p>Or copy and paste this link into your browser:<br/>
            <span style="word-break: break-all; color: #666;">{{ reset_url }}</span>
        </p>
        <p>
            <u>Note</u>: This link will expire in 1 hour.
        </p>
        <p>If you didn't request this password reset, you can safely ignore this email.</p>
        <hr/>
        <div class="footer">
            <p>
                This is an automated message from {{ instance_name }}.
                Please do not reply directly – contact our support instead.
                Thank you!
            </p>
        </div>
    </div>
</body>
</html>