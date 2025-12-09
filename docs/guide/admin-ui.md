# Admin UI

TinyBase includes a modern admin interface for managing your application through a web browser.

## Overview

The Admin UI is:

- **Built with Vue 3, Pinia, and Vite**
- **Single-page application** served by TinyBase
- **Responsive** design for desktop and mobile
- **Included** in the TinyBase package

## Accessing the Admin UI

After starting TinyBase, access the Admin UI at:

```
http://localhost:8000/admin
```

Log in with your admin credentials.

## Dashboard

The dashboard provides an overview of your TinyBase instance:

- **Collections count** - Number of defined collections
- **Records count** - Total records across all collections
- **Users count** - Registered users
- **Functions count** - Registered functions
- **Recent function calls** - Latest executions

## Collections Management

### Viewing Collections

1. Click **Collections** in the sidebar
2. See all collections with record counts
3. Click a collection to view details

### Creating a Collection

1. Click **New Collection**
2. Enter:
   - **Name**: URL-safe identifier (e.g., `blog_posts`)
   - **Label**: Human-readable name (e.g., "Blog Posts")
3. Define the schema in JSON format
4. Configure access rules (optional)
5. Click **Create**

### Schema Editor

The schema editor accepts JSON defining your collection fields:

```json
{
  "fields": [
    {
      "name": "title",
      "type": "string",
      "required": true,
      "max_length": 200
    },
    {
      "name": "content",
      "type": "string",
      "required": true
    },
    {
      "name": "published",
      "type": "boolean",
      "default": false
    },
    {
      "name": "views",
      "type": "integer",
      "default": 0
    }
  ]
}
```

### Managing Records

Within a collection:

1. **View records** - Paginated list with data preview
2. **Create record** - Form based on schema
3. **Edit record** - Modify existing data
4. **Delete record** - Remove with confirmation

## Users Management

### Viewing Users

1. Click **Users** in the sidebar
2. See all registered users
3. Filter by admin status

### User Details

Click a user to see:

- User ID and email
- Admin status
- Creation date
- Associated records (as owner)

### User Actions

- **Grant/revoke admin** - Toggle admin status
- **Delete user** - Remove user account

!!! warning "Deleting Users"
    Deleting a user does not delete their owned records. Records will have `owner_id = null`.

## Functions

### Viewing Functions

1. Click **Functions** in the sidebar
2. See all registered functions with:
   - Name and description
   - Auth level
   - Tags
   - File location

### Function Details

Click a function to see:

- Full description
- Input/output model schemas
- Recent executions
- Execution statistics

### Testing Functions

From the function detail page:

1. Click **Test Function**
2. Enter JSON payload
3. Click **Execute**
4. View the result

## Schedules

### Viewing Schedules

1. Click **Schedules** in the sidebar
2. See all scheduled tasks with:
   - Function name
   - Schedule type
   - Next run time
   - Enabled status

### Creating a Schedule

1. Click **New Schedule**
2. Select the function
3. Choose schedule type:
   - **Once** - Specific date and time
   - **Interval** - Every N seconds/minutes/hours/days
   - **Cron** - Cron expression
4. Configure timezone
5. Set the payload (optional)
6. Enable and save

### Managing Schedules

- **Enable/disable** - Toggle without deleting
- **Edit** - Modify schedule configuration
- **Delete** - Remove the schedule

## Function Calls

### Viewing Function Calls

1. Click **Function Calls** in the sidebar
2. See execution history with:
   - Function name
   - Status (succeeded/failed)
   - Duration
   - Trigger type
   - Timestamp

### Filtering

Filter function calls by:

- Function name
- Status
- Trigger type (manual/schedule)
- Date range

### Call Details

Click a call to see:

- Full execution details
- Input payload
- Output/error
- Duration breakdown

## Settings

The Settings page allows you to configure instance-wide settings.

### General Settings

- **Instance Name** - The name displayed in the admin UI and API responses

### Authentication Settings

- **Allow Public Registration** - Enable/disable public user registration

### Timezone Settings

- **Server Timezone** - Default timezone for scheduled functions

### Scheduler Settings

- **Token Cleanup Interval** - How often to run token cleanup (in scheduler ticks). For example, if the scheduler runs every 5 seconds and this is set to 60, cleanup runs every 5 minutes (60 × 5s).

### Storage Settings

- **File Storage** - Configure S3-compatible file storage settings

### Server Info

View TinyBase configuration:

- Version
- Server host/port
- Database path
- Scheduler status

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Quick search |
| `Escape` | Close modal |
| `Enter` | Confirm action |

## Customizing the Admin UI

### Using Custom Static Files

Point to custom admin files:

```toml
[admin]
static_dir = "/path/to/custom/admin"
```

### Building Custom Admin

1. Clone the TinyBase repository
2. Navigate to `/app`
3. Install dependencies: `yarn install`
4. Make modifications
5. Build: `yarn build`
6. Copy `dist/` to your custom path

## Troubleshooting

### Can't Access Admin UI

1. Verify server is running
2. Check URL: `http://localhost:8000/admin`
3. Clear browser cache
4. Check for JavaScript errors in browser console

### Login Issues

1. Verify admin credentials
2. Check user has `is_admin = true`
3. Try creating a new admin: `tinybase admin add email password`

### UI Not Loading

1. Check `admin.static_dir` configuration
2. Verify static files exist
3. Check server logs for errors

## Mobile Access

The Admin UI is responsive and works on mobile devices:

- Collapsible sidebar
- Touch-friendly controls
- Readable on small screens

For best experience on mobile:

1. Use landscape orientation for tables
2. Use the sidebar toggle button
3. Use filters to reduce data displayed

## Security Considerations

### Session Management

- Tokens stored in browser localStorage
- Cleared on logout
- Expire based on TTL configuration

### Access Control

- Admin UI requires admin login
- All actions authenticated via API
- Rate limiting applies to UI requests

### Best Practices

1. Use HTTPS in production
2. Set strong admin passwords
3. Limit admin user count
4. Review function calls regularly

## See Also

- [Authentication Guide](authentication.md) - Admin user setup
- [Collections Guide](collections.md) - Working with data
- [Functions Guide](functions.md) - Managing functions

