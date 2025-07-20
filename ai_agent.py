"""
AI Agent for parsing meeting requests and scheduling conflicts resolution
"""
import json
import re
from datetime import datetime, timedelta
from openai import OpenAI
from vllm import SamplingParams
BASE_URL = f"http://localhost:4000/v1"
MODEL_PATH = "/home/user/Models/meta-llama/Meta-Llama-3.1-8B-Instruct"
client = OpenAI(api_key="NULL", base_url=BASE_URL, timeout=None, max_retries=0)
class AI_AGENT:
    def __init__(self, client, MODEL_PATH):
        self.client = client
        self.model_path = MODEL_PATH
    
    def parse_email(self, email_content):
        """Parse email content to extract meeting details"""
        response = self.client.chat.completions.create(
            model=self.model_path,
            temperature=0.0,
            max_tokens=150, 
            messages=[{
                "role": "user",
                "content": f"""
                Extract meeting details and return as JSON:
                1. participants (emails)
                2. meeting_duration (minutes, default: 30)
                3. time_constraints (day/time)
                4. subject
        
                Email: {email_content}
                """
            }]
        )
        
        try:
            parsed_data = json.loads(response.choices[0].message.content)
            
            # Ensure participants is a list
            if 'participants' in parsed_data:
                if isinstance(parsed_data['participants'], str):
                    parsed_data['participants'] = [email.strip() for email in parsed_data['participants'].split(',')]
                
                # Add @amd.com if missing domain
                processed_participants = []
                for email in parsed_data['participants']:
                    if '@' not in email:
                        email = f"{email}@amd.com"
                    processed_participants.append(email)
                parsed_data['participants'] = processed_participants
            
            # Setting default duration if not specified
            if 'meeting_duration' not in parsed_data or not parsed_data['meeting_duration']:
                parsed_data['meeting_duration'] = 30
                
            return parsed_data
            
        except json.JSONDecodeError:
            # Fallback parsing if AI response is not valid JSON
            return self._fallback_parse(email_content)
    
    def _fallback_parse(self, email_content):
        """Fallback manual parsing if AI fails"""
        # Extract duration
        duration_patterns = [
            r'(\d+)\s*(?:minutes?|mins?)',
            r'half\s*hour',
            r'(\d+)\s*hours?'
        ]
        
        duration = 30  # default
        for pattern in duration_patterns:
            match = re.search(pattern, email_content.lower())
            if match:
                if 'half' in pattern:
                    duration = 30
                elif 'hour' in pattern:
                    duration = int(match.group(1)) * 60
                else:
                    duration = int(match.group(1))
                break
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, email_content)
        
        # Extract names without emails
        name_pattern = r'(?:attendees?:?\s*|team[,:]?\s*)([A-Za-z\s,&]+)'
        name_match = re.search(name_pattern, email_content, re.IGNORECASE)
        if name_match:
            names = re.split(r'[,&]', name_match.group(1))
            for name in names:
                name = name.strip()
                if name and '@' not in name:
                    emails.append(f"{name.lower()}@amd.com")
        
        # Extract time constraints including weekend detection
        time_constraints = 'next available time'
        email_lower = email_content.lower()
        if 'saturday' in email_lower:
            time_constraints = 'saturday'
        elif 'sunday' in email_lower:
            time_constraints = 'sunday'
        elif 'weekend' in email_lower:
            time_constraints = 'weekend'
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
            'participants': emails,
            'meeting_duration': duration,
            'time_constraints': time_constraints,
            'subject': 'Meeting',
            'start_time': None
        }
    
    def resolve_conflicts(self, all_participants_events, meeting_request, meeting_duration):
        
        # Prepare context for AI
        conflict_context = {
            'meeting_subject': meeting_request.get('subject', ''),
            'participants_events': all_participants_events,
            'meeting_duration': meeting_duration,
            'requested_time': meeting_request.get('time_constraints', '')
        }
        
        response = self.client.chat.completions.create(
            model=self.model_path,
            temperature=0.0,
            messages=[{
                "role": "user",
                "content": f"""
                You are an AI scheduling assistant that resolves meeting conflicts intelligently.
                
                Meeting Request: {meeting_request.get('subject', 'Meeting')}
                Duration: {meeting_duration} minutes
                Time Constraint: {meeting_request.get('time_constraints', 'flexible')}
                
                Participant Events: {json.dumps(all_participants_events, indent=2)}
                
                Rules for conflict resolution:
                1. If all participants are free at requested time -> schedule at requested time
                2. If one person is busy with low-priority meeting -> schedule with available participants first
                3. If person is busy with high-priority meeting -> find alternative time when all are free
                4. If both are busy -> reschedule to next day at same time
                5. Consider meeting importance based on subjects like 'urgent', 'client', 'critical'
                
                Return JSON with:
                - 'action': 'schedule_all', 'schedule_partial', 'reschedule_tomorrow', 'find_alternative'
                - 'recommended_time': 'YYYY-MM-DDTHH:MM:SS+05:30'
                - 'participants_to_include': list of emails
                - 'reason': explanation of decision
                
                Current date context: July 2025
                """
            }]
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except:
            # Fallback decision making
            return self._fallback_conflict_resolution(all_participants_events, meeting_request, meeting_duration)
    
    def _fallback_conflict_resolution(self, all_participants_events, meeting_request, meeting_duration):
        """Fallback conflict resolution logic"""
        available_participants = []
        busy_participants = []
        
        # Checking who's available
        for participant, events in all_participants_events.items():
            if not events:  # No events = available
                available_participants.append(participant)
            else:
                busy_participants.append(participant)
        
        if len(available_participants) == len(all_participants_events):
            # All available
            return {
                'action': 'schedule_all',
                'recommended_time': self._get_next_available_slot(meeting_duration),
                'participants_to_include': list(all_participants_events.keys()),
                'reason': 'All participants are available'
            }
        elif len(available_participants) >= 1:
            # Some available
            return {
                'action': 'schedule_partial',
                'recommended_time': self._get_next_available_slot(meeting_duration),
                'participants_to_include': available_participants,
                'reason': f'Scheduling with available participants: {", ".join(available_participants)}'
            }
        else:
            # All busy - reschedule tomorrow
            tomorrow_time = self._get_tomorrow_slot(meeting_duration)
            return {
                'action': 'reschedule_tomorrow',
                'recommended_time': tomorrow_time,
                'participants_to_include': list(all_participants_events.keys()),
                'reason': 'All participants busy, rescheduling to tomorrow'
            }
    
    def _get_next_available_slot(self, duration_mins):
        """Get next available time slot"""
        now = datetime.now()
        # Round up to next hour
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    
    def _get_tomorrow_slot(self, duration_mins):
        """Get tomorrow's time slot"""
        tomorrow = datetime.now() + timedelta(days=1)
        morning_slot = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        return morning_slot.strftime('%Y-%m-%dT%H:%M:%S+05:30')
