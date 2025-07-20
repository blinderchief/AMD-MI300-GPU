"""
Calendar Event Extraction Module
"""
import json
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def is_weekend(date_obj):
    """
    Check if a given date falls on weekend (Saturday=5, Sunday=6)
    
    Args:
        date_obj (datetime): Date to check
        
    Returns:
        bool: True if weekend, False otherwise
    """
    return date_obj.weekday() >= 5  # Saturday=5, Sunday=6

def check_weekend_constraint(time_constraint):
    """
    Check if the time constraint explicitly requests a weekend
    
    Args:
        time_constraint (str): Natural language time constraint
        
    Returns:
        bool: True if weekend is requested
    """
    constraint_lower = time_constraint.lower()
    weekend_keywords = ['saturday', 'sunday', 'weekend', 'sat', 'sun']
    return any(keyword in constraint_lower for keyword in weekend_keywords)

def retrive_calendar_events(user, start, end):
    """
    Retrieve calendar events for a user within a date range
    
    Args:
        user (str): User email address
        start (str): Start time in ISO format
        end (str): End time in ISO format
    
    Returns:
        list: List of calendar events
    """
    events_list = []
    
    try:
        # Load user credentials
        token_path = f"Keys/{user.split('@')[0]}.token"
        user_creds = Credentials.from_authorized_user_file(token_path)
        
        # Build calendar service
        calendar_service = build("calendar", "v3", credentials=user_creds)
        
        # Fetch events
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        for event in events:
            attendee_list = []
            
            try:
                # Extract attendees
                for attendee in event.get("attendees", []):
                    attendee_list.append(attendee['email'])
            except:
                attendee_list.append("SELF")
            
            # Extract event times
            start_time = event["start"].get("dateTime", event["start"].get("date"))
            end_time = event["end"].get("dateTime", event["end"].get("date"))
            
            events_list.append({
                "StartTime": start_time,
                "EndTime": end_time,
                "NumAttendees": len(set(attendee_list)),
                "Attendees": list(set(attendee_list)),
                "Summary": event.get("summary", "No Title")
            })
            
    except Exception as e:
        print(f"Error retrieving calendar events for {user}: {str(e)}")
        # Return empty list if error (user might not have token file)
        return []
    
    return events_list

def get_date_range_from_constraint(time_constraint, duration_mins=30):
    """
    Convert time constraint to start and end datetime strings
    
    Args:
        time_constraint (str): Natural language time constraint
        duration_mins (int): Meeting duration in minutes
    
    Returns:
        tuple: (start_time, end_time) in ISO format or (None, None) if weekend
    """
    now = datetime.now()
    
    # Default to looking at next 7 days
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=7)
    
    # Parse common time constraints
    constraint_lower = time_constraint.lower()
    
    # Check for explicit weekend requests first
    if check_weekend_constraint(time_constraint):
        return None, None
    
    if 'tomorrow' in constraint_lower:
        tomorrow = now + timedelta(days=1)
        # Check if tomorrow is weekend
        if is_weekend(tomorrow):
            return None, None
        start_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
    
    elif 'next week' in constraint_lower:
        next_week = now + timedelta(days=7)
        start_time = next_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=7)
    
    elif 'saturday' in constraint_lower or 'sunday' in constraint_lower:
        # Explicit weekend request
        return None, None
    
    elif 'thursday' in constraint_lower:
        # Find next Thursday
        days_ahead = 3 - now.weekday()  # Thursday is 3
        if days_ahead <= 0:
            days_ahead += 7
        thursday = now + timedelta(days=days_ahead)
        start_time = thursday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = thursday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    elif 'monday' in constraint_lower:
        # Find next Monday
        days_ahead = 0 - now.weekday()  # Monday is 0
        if days_ahead <= 0:
            days_ahead += 7
        monday = now + timedelta(days=days_ahead)
        start_time = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = monday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    elif 'tuesday' in constraint_lower:
        # Find next Tuesday
        days_ahead = 1 - now.weekday()  # Tuesday is 1
        if days_ahead <= 0:
            days_ahead += 7
        tuesday = now + timedelta(days=days_ahead)
        start_time = tuesday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = tuesday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    elif 'wednesday' in constraint_lower:
        # Find next Wednesday
        days_ahead = 2 - now.weekday()  # Wednesday is 2
        if days_ahead <= 0:
            days_ahead += 7
        wednesday = now + timedelta(days=days_ahead)
        start_time = wednesday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = wednesday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    elif 'friday' in constraint_lower:
        # Find next Friday
        days_ahead = 4 - now.weekday()  # Friday is 4
        if days_ahead <= 0:
            days_ahead += 7
        friday = now + timedelta(days=days_ahead)
        start_time = friday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = friday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Convert to ISO format with timezone
    start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    
    return start_iso, end_iso

def check_time_conflict(event_start, event_end, proposed_start, proposed_end):
    """
    Check if two time periods conflict
    
    Args:
        event_start (str): Existing event start time
        event_end (str): Existing event end time
        proposed_start (str): Proposed meeting start time
        proposed_end (str): Proposed meeting end time
    
    Returns:
        bool: True if there's a conflict
    """
    try:
        # Parse datetime strings
        evt_start = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
        evt_end = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
        prop_start = datetime.fromisoformat(proposed_start.replace('Z', '+00:00'))
        prop_end = datetime.fromisoformat(proposed_end.replace('Z', '+00:00'))
        
        # Check for overlap
        return not (evt_end <= prop_start or evt_start >= prop_end)
    
    except:
        # If parsing fails, assume no conflict
        return False

def find_free_slots(events, duration_mins, start_time, end_time):
    """
    Find free time slots in a day
    
    Args:
        events (list): List of calendar events
        duration_mins (int): Required duration in minutes
        start_time (str): Day start time
        end_time (str): Day end time
    
    Returns:
        list: List of available time slots
    """
    free_slots = []
    
    try:
        day_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        day_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Working hours: 9 AM to 6 PM
        work_start = day_start.replace(hour=9, minute=0)
        work_end = day_start.replace(hour=18, minute=0)
        
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x['StartTime'])
        
        # Check slot before first event
        if not sorted_events or datetime.fromisoformat(sorted_events[0]['StartTime'].replace('Z', '+00:00')) > work_start + timedelta(minutes=duration_mins):
            free_slots.append({
                'start': work_start.isoformat(),
                'end': (work_start + timedelta(minutes=duration_mins)).isoformat()
            })
        
        # Check slots between events
        for i in range(len(sorted_events) - 1):
            event_end = datetime.fromisoformat(sorted_events[i]['EndTime'].replace('Z', '+00:00'))
            next_event_start = datetime.fromisoformat(sorted_events[i + 1]['StartTime'].replace('Z', '+00:00'))
            
            gap_duration = (next_event_start - event_end).total_seconds() / 60
            
            if gap_duration >= duration_mins:
                free_slots.append({
                    'start': event_end.isoformat(),
                    'end': (event_end + timedelta(minutes=duration_mins)).isoformat()
                })
        
        # Check slot after last event
        if sorted_events:
            last_event_end = datetime.fromisoformat(sorted_events[-1]['EndTime'].replace('Z', '+00:00'))
            if last_event_end + timedelta(minutes=duration_mins) <= work_end:
                free_slots.append({
                    'start': last_event_end.isoformat(),
                    'end': (last_event_end + timedelta(minutes=duration_mins)).isoformat()
                })
    
    except Exception as e:
        print(f"Error finding free slots: {str(e)}")
    
    return free_slots
