"""
Main Meeting Assistant Module
Integrates all components for complete AI scheduling functionality
"""
import json
import sys
import os
import time 
from datetime import datetime
from openai import OpenAI

# I used it to add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent import AI_AGENT
from calendar_utils import retrive_calendar_events, get_date_range_from_constraint
from conflict_resolver import ConflictResolver
from output_formatter import OutputFormatter

class MeetingAssistant:
    def __init__(self):
        # Initialize AI client
        self.base_url = "http://localhost:4000/v1"
        self.model_path = "/home/user/Models/meta-llama/Meta-Llama-3.1-8B-Instruct"
        try:
            self.client = OpenAI(api_key="NULL", base_url=self.base_url, timeout=3, max_retries=1)  # Fast timeout
            self.ai_agent = AI_AGENT(self.client, self.model_path)
        except Exception as e:
            print(f"Warning: AI client initialization failed: {e}")
            self.client = None
            self.ai_agent = None
        
        # Initialize other components
        self.conflict_resolver = ConflictResolver(self.ai_agent)
        self.output_formatter = OutputFormatter()
    
    def your_meeting_assistant(self, data):
        """
        Main meeting assistant function that processes incoming requests
        Args:
            data (dict): Input JSON data with meeting request
        Returns:
            dict: Formatted response with meeting schedule
        """
        try:
            start_time = time.time()  # Start timing
            
            print(f"\\n=== Processing Meeting Request ===")
            print(f"Request ID: {data.get('Request_id', 'N/A')}")
            print(f"Subject: {data.get('Subject', 'N/A')}")
            
            # Step 1: Parse the meeting request
            parse_start = time.time()
            parsed_request = self._parse_meeting_request(data)
            parse_time = time.time() - parse_start
            print(f"\\nParsing took: {parse_time:.2f} seconds")
            
            # Step 2: Get calendar events for all participants
            calendar_start = time.time()
            all_participants_events = self._get_all_participants_events(parsed_request)
            calendar_time = time.time() - calendar_start
            print(f"Calendar fetch took: {calendar_time:.2f} seconds")
            
            # Step 3: Resolve conflicts
            resolve_start = time.time()
            resolution_result = self._resolve_conflicts(parsed_request, all_participants_events)
            resolve_time = time.time() - resolve_start
            print(f"Conflict resolution took: {resolve_time:.2f} seconds")
            
            # Step 4: Format output
            format_start = time.time()
            final_output = self._format_final_output(data, resolution_result, all_participants_events)
            format_time = time.time() - format_start
            print(f"Formatting took: {format_time:.2f} seconds")
            
            total_time = time.time() - start_time
            print(f"\\n✅ TOTAL TIME: {total_time:.2f} seconds")
            
            if total_time > 10.0:
                print(f"⚠️ WARNING: Response time {total_time:.2f}s exceeds 10s target!")
            
            return final_output
            
        except Exception as e:
            print(f"Error in meeting assistant: {str(e)}")
            
            # Special handling for weekend requests
            if "WEEKEND_MEETING_REQUESTED" in str(e):
                return self._create_weekend_rejection_response(data)
            
            return self._create_error_response(data, str(e))
    
    def _parse_meeting_request(self, data):
        """Parse meeting request - Manual first, then AI if needed"""
        
        # FAST MANUAL PARSING FIRST (most reliable for speed)
        manual_result = self._manual_parse_request(data)
        
        # Only use AI if manual parsing is too vague AND we have AI available
        if self.ai_agent and manual_result['time_constraints'] == 'next available time':
            try:
                print("   Using AI for better parsing...")
                email_content = data.get('EmailContent', '')
                ai_parsed_data = self.ai_agent.parse_email(email_content)
                
                # I Merged AI results with manual results
                participants = [data.get('From', '')] + [att['email'] for att in data.get('Attendees', [])]
                participants = list(set(participants))
                
                parsed_request = {
                    'participants': participants,
                    'meeting_duration': ai_parsed_data.get('meeting_duration', manual_result['meeting_duration']),
                    'time_constraints': ai_parsed_data.get('time_constraints', manual_result['time_constraints']),
                    'subject': data.get('Subject', ai_parsed_data.get('subject', 'Meeting')),
                    'start_time': ai_parsed_data.get('start_time'),
                    'From': data.get('From', '')
                }
                return parsed_request
                
            except Exception as e:
                print(f"   AI parsing failed, using manual: {e}")
        
        return manual_result
    
    def _manual_parse_request(self, data):
        """Manual parsing when AI is not available"""
        participants = [data.get('From', '')] + [att['email'] for att in data.get('Attendees', [])]
        participants = list(set(participants))
        
        # Extract duration from email content
        email_content = data.get('EmailContent', '').lower()
        duration = 30  # default
        
        if '30 minutes' in email_content or 'half hour' in email_content:
            duration = 30
        elif '1 hour' in email_content or 'an hour' in email_content:
            duration = 60
        elif '15 minutes' in email_content:
            duration = 15
        
        # Extract time constraints including weekend detection
        time_constraints = 'next available time'
        email_lower = email_content.lower()
        
        # Check for weekends first
        if any(word in email_lower for word in ['saturday', 'sunday', 'weekend']):
            time_constraints = 'weekend'
        # Check for specific days
        elif 'thursday' in email_lower:
            time_constraints = 'thursday'
        elif 'monday' in email_lower:
            time_constraints = 'monday'
        elif 'tuesday' in email_lower:
            time_constraints = 'tuesday'
        elif 'wednesday' in email_lower:
            time_constraints = 'wednesday'
        elif 'friday' in email_lower:
            time_constraints = 'friday'
        elif 'tomorrow' in email_lower:
            time_constraints = 'tomorrow'
        
        return {
            'participants': participants,
            'meeting_duration': duration,
            'time_constraints': time_constraints,
            'subject': data.get('Subject', 'Meeting'),
            'start_time': None,
            'From': data.get('From', '')
        }
    
    def _get_all_participants_events(self, parsed_request):
        """Retrieve calendar events for all participants"""
        all_events = {}
        
        # weekend check first - saves time
        if parsed_request['time_constraints'] == 'weekend':
            raise ValueError("WEEKEND_MEETING_REQUESTED")
        
        # Get date range based on time constraints
        start_time, end_time = get_date_range_from_constraint(
            parsed_request['time_constraints'], 
            parsed_request['meeting_duration']
        )
        
        # Check if weekend was requested
        if start_time is None and end_time is None:
            print(f"Weekend meeting requested - rejecting")
            raise ValueError("WEEKEND_MEETING_REQUESTED")
        
        print(f"Checking calendars from {start_time} to {end_time}")
        
        # SIMPLE PARALLEL FETCHING for speed
        import threading
        threads = []
        results = {}
        
        def fetch_calendar(participant):
            try:
                events = retrive_calendar_events(participant, start_time, end_time)
                results[participant] = events
                print(f"  {participant}: {len(events)} events found")
            except Exception as e:
                print(f"  {participant}: Calendar access failed ({e})")
                results[participant] = []  # Assume available if can't access calendar
        
        # Start all calendar fetches in parallel
        for participant in parsed_request['participants']:
            thread = threading.Thread(target=fetch_calendar, args=(participant,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete (max 3 seconds)
        for thread in threads:
            thread.join(timeout=3)
        
        return results
    
    def _resolve_conflicts(self, parsed_request, all_participants_events):
        """Resolve scheduling conflicts"""
        return self.conflict_resolver.resolve_scheduling_conflicts(
            parsed_request,
            all_participants_events,
            parsed_request['meeting_duration']
        )
    
    def _format_final_output(self, original_data, resolution_result, all_participants_events):
        """Format the final output"""
        return self.output_formatter.format_output(
            original_data,
            resolution_result,
            all_participants_events
        )
    
    def _create_weekend_rejection_response(self, data):
        """Create response for weekend meeting requests"""
        return {
            "Request_id": data.get("Request_id", ""),
            "Datetime": data.get("Datetime", ""),
            "Location": data.get("Location", ""),
            "From": data.get("From", ""),
            "Attendees": data.get("Attendees", []),
            "Subject": data.get("Subject", ""),
            "EmailContent": data.get("EmailContent", ""),
            "EventStart": "",
            "EventEnd": "",
            "Duration_mins": "",
            "MetaData": {
                "status": "rejected",
                "reason": "Its weekends no meetings are possible",
                "message": "Weekend meetings are not allowed. Please schedule during business days (Monday-Friday)."
            }
        }
    
    def _create_error_response(self, data, error_message):
        """Create error response when processing fails"""
        return {
            "Request_id": data.get("Request_id", ""),
            "Datetime": data.get("Datetime", ""),
            "Location": data.get("Location", ""),
            "From": data.get("From", ""),
            "Attendees": data.get("Attendees", []),
            "Subject": data.get("Subject", ""),
            "EmailContent": data.get("EmailContent", ""),
            "EventStart": "",
            "EventEnd": "",
            "Duration_mins": "30",
            "MetaData": {
                "error": error_message,
                "status": "failed"
            }
        }

# For backward compatibility and easy testing
def your_meeting_assistant(data):
    """
    Wrapper function for the meeting assistant
    This function is called from the Flask server
    """
    assistant = MeetingAssistant()
    return assistant.your_meeting_assistant(data)
