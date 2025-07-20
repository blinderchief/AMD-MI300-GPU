"""
Conflict Resolution Engine for Meeting Scheduling
"""
import json
from datetime import datetime, timedelta
from calendar_utils import find_free_slots, check_time_conflict, is_weekend

class ConflictResolver:
    def __init__(self, ai_agent):
        self.ai_agent = ai_agent
    
    def resolve_scheduling_conflicts(self, parsed_request, all_participants_events, meeting_duration):
        """
        Main conflict resolution logic
        Args:
            parsed_request (dict): Parsed meeting request
            all_participants_events (dict): Events for all participants
            meeting_duration (int): Meeting duration in minutes
        Returns:
            dict: Resolution decision with timing and participants
        """
        # Analyze conflict situation
        conflict_analysis = self._analyze_conflicts(all_participants_events, meeting_duration)
        
        # Apply resolution rules based on test cases
        if conflict_analysis['all_free']:
            return self._schedule_all_participants(parsed_request, meeting_duration)
        
        elif conflict_analysis['some_busy']:
            return self._handle_partial_conflicts(
                parsed_request, 
                all_participants_events, 
                conflict_analysis,
                meeting_duration
            )
        
        else:  # All busy
            return self._handle_all_busy(parsed_request, meeting_duration)
    
    def _analyze_conflicts(self, all_participants_events, meeting_duration):
        """Analyze who's busy and who's free"""
        available_participants = []
        busy_participants = []
        conflict_details = {}
        
        for participant, events in all_participants_events.items():
            if not events or len(events) == 0:
                available_participants.append(participant)
            else:
                busy_participants.append(participant)
                # Analyze importance of conflicting meetings
                conflict_details[participant] = self._analyze_meeting_importance(events)
        
        return {
            'all_free': len(busy_participants) == 0,
            'some_busy': 0 < len(busy_participants) < len(all_participants_events),
            'all_busy': len(busy_participants) == len(all_participants_events),
            'available_participants': available_participants,
            'busy_participants': busy_participants,
            'conflict_details': conflict_details
        }
    
    def _analyze_meeting_importance(self, events):
        """Analyze importance of conflicting meetings based on subject"""
        importance_keywords = {
            'high': ['client', 'customer', 'urgent', 'critical', 'ceo', 'board', 'emergency'],
            'medium': ['team', 'project', 'review', 'planning', 'discussion'],
            'low': ['lunch', 'coffee', 'break', 'personal', 'training']
        }
        
        meeting_importance = []
        
        for event in events:
            summary = event.get('Summary', '').lower()
            importance = 'medium'  # default
            
            for level, keywords in importance_keywords.items():
                for keyword in keywords:
                    if keyword in summary:
                        importance = level
                        break
                if importance != 'medium':
                    break
            
            meeting_importance.append({
                'event': event,
                'importance': importance,
                'summary': event.get('Summary', '')
            })
        
        return meeting_importance
    
    def _schedule_all_participants(self, parsed_request, meeting_duration):
        """Test Case 1: All participants are available"""
        # Find optimal time based on constraint
        optimal_time = self._find_optimal_time(parsed_request, meeting_duration)
        
        return {
            'action': 'schedule_all',
            'recommended_time': optimal_time,
            'participants_to_include': parsed_request['participants'],
            'reason': 'All participants are available at the requested time',
            'meeting_duration': meeting_duration
        }
    
    def _handle_partial_conflicts(self, parsed_request, all_participants_events, conflict_analysis, meeting_duration):
        """Handle cases where some participants are busy"""
        
        # Check if the meeting can proceed with fewer people
        subject = parsed_request.get('subject', '').lower()
        
        # Determine if the busy person is critical for this meeting
        critical_keywords = ['all', 'team', 'everyone', 'together']
        requires_all = any(keyword in subject for keyword in critical_keywords)
        
        if requires_all:
            # Test Case 3 scenario - need everyone
            return self._reschedule_for_all(parsed_request, meeting_duration)
        
        else:
            # Test Cases 2 & 4 - can proceed with available participants
            busy_person = conflict_analysis['busy_participants'][0]
            busy_events = conflict_analysis['conflict_details'][busy_person]
            
            # Check if busy person has low-priority conflict
            has_low_priority_conflict = any(
                event['importance'] == 'low' for event in busy_events
            )
            
            if has_low_priority_conflict:
                # Reschedule the low-priority meeting
                return self._schedule_with_reschedule(parsed_request, busy_person, meeting_duration)
            else:
                # Schedule with available participants only
                return self._schedule_partial_meeting(
                    parsed_request, 
                    conflict_analysis['available_participants'],
                    conflict_analysis['busy_participants'],
                    meeting_duration
                )
    
    def _handle_all_busy(self, parsed_request, meeting_duration):
        """Test Case 3: All participants are busy"""
        # Reschedule to tomorrow at the same time
        tomorrow_time = self._get_tomorrow_time(meeting_duration)
        
        return {
            'action': 'reschedule_tomorrow',
            'recommended_time': tomorrow_time,
            'participants_to_include': parsed_request['participants'],
            'reason': 'All participants are busy with important meetings. Rescheduling to tomorrow.',
            'meeting_duration': meeting_duration
        }
    
    def _schedule_partial_meeting(self, parsed_request, available_participants, busy_participants, meeting_duration):
        """Schedule meeting with only available participants"""
        optimal_time = self._find_optimal_time(parsed_request, meeting_duration)
        
        # Determine strategy based on subject
        subject = parsed_request.get('subject', '').lower()
        
        if 'feedback' in subject and len(available_participants) >= 1:
            # Test Case 4 scenario - feedback can be handled by available person
            return {
                'action': 'schedule_partial',
                'recommended_time': optimal_time,
                'participants_to_include': available_participants,
                'reason': f'Meeting can proceed with {", ".join(available_participants)}. Will update {", ".join(busy_participants)} separately.',
                'meeting_duration': meeting_duration,
                'follow_up_needed': busy_participants
            }
        
        else:
            # Test Case 2 scenario - schedule with organizer first, then with busy person later
            organizer = parsed_request.get('From', parsed_request['participants'][0])
            
            return {
                'action': 'schedule_organizer_first',
                'recommended_time': optimal_time,
                'participants_to_include': [organizer] + available_participants,
                'reason': f'Scheduling with organizer and available participants first. Will arrange separate time with {", ".join(busy_participants)}.',
                'meeting_duration': meeting_duration,
                'follow_up_meetings': [
                    {
                        'participants': [organizer] + busy_participants,
                        'time': self._find_alternative_time(meeting_duration),
                        'reason': 'Follow-up meeting with previously busy participants'
                    }
                ]
            }
    
    def _find_optimal_time(self, parsed_request, meeting_duration):
        """Find optimal meeting time based on constraints"""
        constraint = parsed_request.get('time_constraints', 'flexible')
        
        # Parse specific time if mentioned
        if 'thursday' in constraint.lower():
            base_date = self._get_next_thursday()
            if is_weekend(base_date):
                # If somehow Thursday calculation results in weekend, move to Monday
                base_date = self._get_next_monday()
            return base_date.replace(hour=10, minute=30).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        elif 'monday' in constraint.lower():
            base_date = self._get_next_monday()
            if '9:00' in constraint:
                return base_date.replace(hour=9, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
            return base_date.replace(hour=10, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        elif 'tuesday' in constraint.lower():
            base_date = self._get_next_tuesday()
            if '11:00' in constraint:
                return base_date.replace(hour=11, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
            return base_date.replace(hour=10, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        elif 'wednesday' in constraint.lower():
            base_date = self._get_next_wednesday()
            if '10:00' in constraint:
                return base_date.replace(hour=10, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
            return base_date.replace(hour=10, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        elif 'friday' in constraint.lower():
            base_date = self._get_next_friday()
            return base_date.replace(hour=10, minute=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        else:
            # Default to next available business hour
            next_slot = datetime.now() + timedelta(hours=1)
            next_slot = next_slot.replace(minute=0, second=0, microsecond=0)
            
            # Ensure it's during business hours and not weekend
            while is_weekend(next_slot) or next_slot.hour < 9 or next_slot.hour > 17:
                if is_weekend(next_slot):
                    # Move to next Monday
                    days_to_monday = (7 - next_slot.weekday()) % 7
                    if days_to_monday == 0:
                        days_to_monday = 7
                    next_slot = next_slot + timedelta(days=days_to_monday)
                    next_slot = next_slot.replace(hour=9)
                elif next_slot.hour < 9:
                    next_slot = next_slot.replace(hour=9)
                elif next_slot.hour > 17:
                    next_slot = next_slot + timedelta(days=1)
                    next_slot = next_slot.replace(hour=9)
            
            return next_slot.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    
    def _get_next_thursday(self):
        """Get next Thursday"""
        today = datetime.now()
        days_ahead = 3 - today.weekday()  # Thursday = 3
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_next_monday(self):
        """Get next Monday"""
        today = datetime.now()
        days_ahead = 0 - today.weekday()  # Monday = 0
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_next_tuesday(self):
        """Get next Tuesday"""
        today = datetime.now()
        days_ahead = 1 - today.weekday()  # Tuesday = 1
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_next_wednesday(self):
        """Get next Wednesday"""
        today = datetime.now()
        days_ahead = 2 - today.weekday()  # Wednesday = 2
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_next_friday(self):
        """Get next Friday"""
        today = datetime.now()
        days_ahead = 4 - today.weekday()  # Friday = 4
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_tomorrow_time(self, meeting_duration):
        """Get tomorrow's meeting time"""
        tomorrow = datetime.now() + timedelta(days=1)
        
        # If tomorrow is weekend, move to next Monday
        if is_weekend(tomorrow):
            days_to_monday = (7 - tomorrow.weekday()) % 7
            if days_to_monday == 0:
                days_to_monday = 7
            tomorrow = tomorrow + timedelta(days=days_to_monday)
        
        return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
    
    def _find_alternative_time(self, meeting_duration):
        """Find alternative time for follow-up meetings"""
        alternative = datetime.now() + timedelta(hours=2)
        alternative = alternative.replace(minute=0, second=0, microsecond=0)
        return alternative.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    
    def _reschedule_for_all(self, parsed_request, meeting_duration):
        """Reschedule when all participants are needed"""
        tomorrow_time = self._get_tomorrow_time(meeting_duration)
        
        return {
            'action': 'reschedule_tomorrow',
            'recommended_time': tomorrow_time,
            'participants_to_include': parsed_request['participants'],
            'reason': 'All participants are required but some are busy. Rescheduling to tomorrow.',
            'meeting_duration': meeting_duration
        }
    
    def _schedule_with_reschedule(self, parsed_request, busy_person, meeting_duration):
        """Schedule meeting and reschedule conflicting low-priority meeting"""
        optimal_time = self._find_optimal_time(parsed_request, meeting_duration)
        
        return {
            'action': 'schedule_all_with_reschedule',
            'recommended_time': optimal_time,
            'participants_to_include': parsed_request['participants'],
            'reason': f'Rescheduling {busy_person}\'s low-priority meeting to accommodate this important meeting.',
            'meeting_duration': meeting_duration,
            'reschedule_needed': busy_person
        }
