from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen
import json

def get_current_time() -> str:
    """
    Retrieves the current date, time, and timezone information.
    Returns a formatted string with local time in both 12-hour and ISO formats,
    along with timezone abbreviation.
    """
    try:
        # Get timezone information
        with urlopen('https://ipapi.co/json/') as response:
            ip_data = json.loads(response.read().decode())
        timezone = ip_data.get('timezone', 'UTC')
        
        # Get current time in the detected timezone
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        
        # Get timezone abbreviation (like EST, EDT, IST)
        tz_abbrev = now.strftime('%Z')
        
        # Format the response
        return (f"Current local time: {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} {tz_abbrev}\n"
                f"ISO format: {now.isoformat()}")
                
    except Exception as e:
        # Fallback to UTC if there's any error
        now = datetime.now(ZoneInfo('UTC'))
        return (f"Could not detect local timezone. Current UTC time:\n"
                f"{now.strftime('%A, %B %d, %Y at %I:%M:%S %p')} UTC\n"
                f"ISO format: {now.isoformat()}")

# Example usage
if __name__ == "__main__":
    print(get_current_time())