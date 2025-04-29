import os
from typing import Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("google_calendar")

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Configuration paths
CREDENTIALS_FILE = "/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/credentials.json"
TOKEN_FILE = "/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/token.json"

from datetime import datetime, timedelta
import re

def convert_to_iso_datetime(datetime_str: str) -> str:
    """
    Convert a datetime string to ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    Handles common formats without using dateutil package.
    
    Args:
        datetime_str: String containing date/time (e.g., "2024-12-25 14:00", "2pm")
    
    Returns:
        str: Datetime in ISO 8601 format
    
    Raises:
        ValueError: If the input string cannot be parsed as a valid datetime
    """
    try:
        # Try standard ISO format first
        try:
            dt = datetime.fromisoformat(datetime_str)
            
            return dt.isoformat(timespec='seconds')
        except ValueError:
            pass

        # Current time for relative calculations
        now = datetime.now()
        
        # Handle relative dates (today, tomorrow)
        if datetime_str.lower().startswith('today'):
            time_part = datetime_str[5:].strip()
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif datetime_str.lower().startswith('tomorrow'):
            time_part = datetime_str[8:].strip()
            dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            time_part = datetime_str
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Try to parse date formats
        date_formats = [
            '%Y-%m-%d',    # 2024-12-25
            '%m/%d/%Y',    # 12/25/2024
            '%B %d, %Y',    # December 25, 2024
            '%b %d, %Y',    # Dec 25, 2024
            '%d %B %Y',     # 25 December 2024
        ]
        
        date_parsed = False
        for fmt in date_formats:
            try:
                dt = datetime.strptime(time_part, fmt)
                date_parsed = True
                break
            except ValueError:
                pass
        
        # If no date was found in the string, assume today
        if not date_parsed and not (datetime_str.lower().startswith(('today', 'tomorrow'))):
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            time_part = datetime_str

        # Parse time
        time_formats = [
            '%H:%M',        # 14:00
            '%I:%M%p',      # 2:00PM
            '%I%p',         # 2PM
            '%H:%M:%S',     # 14:00:00
            '%I:%M:%S%p',   # 2:00:00PM
        ]
        
        time_match = re.search(r'(\d{1,2}(?::\d{2}){0,2}\s*[ap]m?)|(\d{1,2}:\d{2}(?::\d{2})?)', time_part, re.IGNORECASE)
        if time_match:
            time_str = time_match.group(0)
            for fmt in time_formats:
                try:
                    time = datetime.strptime(time_str, fmt).time()
                    dt = dt.replace(hour=time.hour, minute=time.minute, second=time.second)
                    break
                except ValueError:
                    pass
        
        # If no time was provided, use current time
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second)

        
        
        return dt.isoformat(timespec='seconds')
    
    except Exception as e:
        raise ValueError(f"Could not parse datetime string '{datetime_str}': {str(e)}")


def get_calendar_service():
    """Get authenticated Google Calendar service"""
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Get new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for next time
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    
    return build("calendar", "v3", credentials=creds)

@mcp.tool()
async def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> str:
    """
    Use this function to create calendar events in Google Calendar with all necessary details. 

    Key guidelines:
    1. Always provide both summary (event title) and valid start/end times in ISO 8601 format (e.g., "2025-04-29T17:48:07.474522")
    2. The timezone is automatically set to EDT - no need to specify timezone
    3. Include any optional parameters when available:
    - description: More details about the event
    - location: Where the event will take place
    - attendees: List of email addresses to invite
    4. The function returns either a clickable event link (success) or an error message

    Example scenarios when to use:
    - When user wants to schedule a meeting, appointment, or reminder
    - When user provides specific date/time information for an event
    - When user mentions inviting others or adding location/details

    Example usage:
    * "Schedule a team meeting tomorrow from 2-3pm about the Q2 roadmap"
    * "Create an event called 'Dentist Appointment' next Tuesday at 9am for 1 hour"
    * "Add a birthday dinner to my calendar for May 5th at 7pm at Olive Garden"
    """

    try:
        service = get_calendar_service()
        
        event = {
        'summary': summary,
        'start': {
            'dateTime': convert_to_iso_datetime(start_time),
            'timeZone': "EST",
        },
        'end': {
            'dateTime': convert_to_iso_datetime(end_time),
            'timeZone': "EST",
        },
    }
        
        # Add optional fields if provided
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]
        
        # Create the event
        created_event = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()
        
        return f"✅ Event created: {created_event.get('htmlLink')}"
    
    except HttpError as error:
        return f"❌ Google API error: {error}"
    except Exception as e:
        return f"❌ Failed to create event: {str(e)}"

if __name__ == "__main__":
    print("📅 Google Calendar Service Starting...")
    mcp.run()