# Google Calendar MCP Client

This repository contains a FastMCP client for interacting with the Google Calendar API. It allows you to create calendar events and search for existing events programmatically.

## Features

- **Authentication**: Manages OAuth 2.0 authentication flow with Google Calendar API
- **Create Events**: Add events to your Google Calendar with details including:
  - Summary (title)
  - Start and end times
  - Description
  - Location
  - Attendees
- **Search Events**: Find events within a specified time period

## Prerequisites

- Python 3.6+
- Google Cloud project with Calendar API enabled
- OAuth 2.0 credentials file

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client fastmcp
   ```
3. Place your Google OAuth credentials file at the specified path:
   ```
   /home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/credentials.json
   ```

## Configuration

The code requires two configuration paths:

```python
CREDENTIALS_FILE = "/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/credentials.json"
TOKEN_FILE = "/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/token.json"
```

- `CREDENTIALS_FILE`: Location of your Google OAuth credentials JSON file
- `TOKEN_FILE`: Where the authentication token will be stored after successful authentication

## API Reference

### `create_event()`

Creates a new event on your primary Google Calendar.

**Parameters:**
- `summary` (str): Title of the event (required)
- `start_time` (str): Event start time (required)
- `end_time` (str): Event end time (required)
- `description` (str, optional): Additional details about the event
- `location` (str, optional): Where the event will take place
- `attendees` (List[str], optional): List of email addresses to invite

**Returns:**
- String containing success message with event link, or error message

**Example Usage:**
```python
result = await create_event(
    summary="Team Meeting",
    start_time="2025-05-01 14:00",
    end_time="2025-05-01 15:00",
    description="Weekly team sync",
    location="Conference Room A",
    attendees=["colleague@example.com"]
)
```

### `search_events()`

Searches for events in your primary Google Calendar within a specified time range.

**Parameters:**
- `start_time` (str, optional): Start of time range in ISO format
- `end_time` (str, optional): End of time range in ISO format

**Returns:**
- String containing formatted event details or error message

**Example Usage:**
```python
events = await search_events(
    start_time="2025-04-30T00:00:00",
    end_time="2025-05-01T23:59:59"
)
```

## Helper Functions

### `convert_to_iso_datetime()`

Converts various datetime string formats to ISO 8601 format.

**Parameters:**
- `datetime_str` (str): String containing date/time in various formats

**Returns:**
- ISO 8601 formatted datetime string

**Supported Input Formats:**
- ISO format: `2024-12-25T14:00:00`
- Date formats: `2024-12-25`, `12/25/2024`, `December 25, 2024`, etc.
- Time formats: `14:00`, `2:00PM`, `2PM`, etc.
- Relative formats: `today`, `tomorrow`, etc.

### `get_calendar_service()`

Handles authentication and returns an authenticated Google Calendar service.

**Returns:**
- Authenticated Google Calendar API service object

### `search_calendar_events()`

Internal helper function that performs the actual event search.

**Parameters:**
- `start_time` (str, optional): Start time in ISO format
- `end_time` (str, optional): End time in ISO format
- `max_results` (int, optional): Maximum number of events to return (default: 10)

**Returns:**
- Tuple containing success status and either list of events or error message

## Future Enhancements

Code contains placeholder functions for potential future functionality:
- Update existing events
- Delete events

## Running the Service

To start the MCP service:

```bash
python calendar_mcp.py
```

This will initialize the FastMCP service with the name "google_calendar".

## Notes

- The timezone is hardcoded to "EST" for all events
- Authentication token will be refreshed automatically when expired
- The service uses the user's primary calendar only
