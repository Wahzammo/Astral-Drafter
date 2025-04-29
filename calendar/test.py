from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def search_calendar_events(start_time=None, end_time=None, max_results=10):
    """
    Search Google Calendar events within a specified time range.
    
    Args:
        start_time (str): ISO format start time (e.g., "2025-05-01T09:00:00")
        end_time (str): ISO format end time (e.g., "2025-05-01T17:00:00")
        max_results (int): Maximum number of events to return (default: 10)
    
    Returns:
        tuple: (success: bool, result: list/str) 
               Where result is either list of events or error message
    """
    try:
        # Initialize credentials
        creds = Credentials.from_authorized_user_file('/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/token.json')
        service = build('calendar', 'v3', credentials=creds)

        # Set default time range (current day) if not specified
        now = datetime.utcnow()
        if not start_time:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        else:
            # Ensure provided start_time is properly formatted
            if 'Z' not in start_time and '+' not in start_time:
                start_time += 'Z'
        
        if not end_time:
            end_time = (now.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(days=1)).isoformat() + 'Z'
        else:
            # Ensure provided end_time is properly formatted
            if 'Z' not in end_time and '+' not in end_time:
                end_time += 'Z'

        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        if not events:
            return (True, [])  # Return empty list rather than error for no events
            
        # Format events data
        formatted_events = []
        for event in events:
            event_data = {
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location', 'Not specified'),
                'description': event.get('description', 'None')[:100] + '...' if event.get('description') else 'None'
            }
            formatted_events.append(event_data)
        
        return (True, formatted_events)

    except HttpError as error:
        error_details = error.content.decode('utf-8') if hasattr(error, 'content') else str(error)
        return (False, f"Google Calendar API error: {error_details}")
    except Exception as e:
        return (False, f"Error searching events: {str(e)}")

# Example usage with proper error handling
if __name__ == "__main__":
    # Search today's events
    print("Today's events:")
    success, result = search_calendar_events()
    
    if success:
        if result:
            for event in result:
                print(f"{event['summary']} from {event['start']} to {event['end']}")
        else:
            print("No events found for today")
    else:
        print("Error:", result)
    
    # Search specific time range (properly formatted)
    print("\nEvents next week:")
    success, result = search_calendar_events(
        start_time="2025-05-05T00:00:00Z",  # Note the 'Z' indicating UTC
        end_time="2025-05-09T23:59:59Z"     # Note the 'Z' indicating UTC
    )
    
    if success:
        if result:
            for event in result:
                print(f"{event['summary']} at {event['location']}")
        else:
            print("No events found for this period")
    else:
        print("Error:", result)