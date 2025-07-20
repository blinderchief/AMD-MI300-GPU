"""
Output formatter for meeting scheduling results
"""
import json
from datetime import datetime, timedelta

class OutputFormatter:
    def __init__(self):
        pass
    
    def format_output(self, original_request, resolution_result, all_participants_events):
        """
        Format the final output in the required JSON structure
        Args:
            original_request (dict): Original meeting request
            resolution_result (dict): Conflict resolution result
            all_participants_events (dict): All participants' calendar events
        Returns:
            dict: Formatted output matching the required structure
        """
        # Calculate end time
        start_time = resolution_result['recommended_time']
        duration_mins = resolution_result['meeting_duration']
        end_time = self._calculate_end_time(start_time, duration_mins)
        
        # Build attendees list with events
        attendees_with_events = self._build_attendees_events(
            resolution_result['participants_to_include'],
            all_participants_events,
            start_time,
            end_time,
            original_request['Subject'],
            original_request
        )
        
        # Build the output structure
        output = {
            "Request_id": original_request.get("Request_id", ""),
            "Datetime": original_request.get("Datetime", ""),
            "Location": original_request.get("Location", ""),
            "From": original_request.get("From", ""),
            "Attendees": attendees_with_events,
            "Subject": original_request.get("Subject", ""),
            "EmailContent": original_request.get("EmailContent", ""),
            "EventStart": start_time,
            "EventEnd": end_time,
            "Duration_mins": str(duration_mins),
            "MetaData": self._build_metadata(resolution_result)
        }
        
        return output
    
    def _calculate_end_time(self, start_time_str, duration_mins):
        """Calculate end time from start time and duration"""
        try:
            # Parse start time
            start_time = datetime.fromisoformat(start_time_str.replace('+05:30', ''))
            
            # Add the duration
            end_time = start_time + timedelta(minutes=duration_mins)
            
            # Format back to string
            return end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        except Exception as e:
            print(f"Error calculating end time: {e}")
            # Fallback
            return start_time_str
    
    def _build_attendees_events(self, included_participants, all_participants_events, meeting_start, meeting_end, meeting_subject, original_request):
        """Build the attendees list with their events including the new meeting"""
        attendees_list = []
        
        # Get all participants from original request
        all_participants = [original_request.get('From', '')] + [att['email'] for att in original_request.get('Attendees', [])]
        all_participants = list(set(all_participants))  # Remove duplicates
        
        for participant in all_participants:
            participant_events = []
            
            # Add existing events
            if participant in all_participants_events:
                participant_events.extend(all_participants_events[participant])
            
            # Add the new meeting if participant is included
            if participant in included_participants:
                new_meeting_event = {
                    "StartTime": meeting_start,
                    "EndTime": meeting_end,
                    "NumAttendees": len(included_participants),
                    "Attendees": included_participants,
                    "Summary": meeting_subject
                }
                participant_events.append(new_meeting_event)
            
            # Sort events by start time
            participant_events.sort(key=lambda x: x.get('StartTime', ''))
            
            attendees_list.append({
                "email": participant,
                "events": participant_events
            })
        
        return attendees_list
    
    def _build_metadata(self, resolution_result):
        """Build metadata with resolution details"""
        metadata = {
            "resolution_action": resolution_result.get('action', ''),
            "resolution_reason": resolution_result.get('reason', ''),
            "scheduling_strategy": self._get_scheduling_strategy(resolution_result)
        }
        
        # Add follow-up information if present
        if 'follow_up_meetings' in resolution_result:
            metadata['follow_up_meetings'] = resolution_result['follow_up_meetings']
        
        if 'follow_up_needed' in resolution_result:
            metadata['follow_up_needed'] = resolution_result['follow_up_needed']
        
        if 'reschedule_needed' in resolution_result:
            metadata['reschedule_needed'] = resolution_result['reschedule_needed']
        
        return metadata
    
    def _get_scheduling_strategy(self, resolution_result):
        """Determine the scheduling strategy used"""
        action = resolution_result.get('action', '')
        
        strategy_map = {
            'schedule_all': 'All participants available - direct scheduling',
            'schedule_partial': 'Partial scheduling with available participants',
            'reschedule_tomorrow': 'All busy - rescheduled to next day',
            'schedule_organizer_first': 'Organizer and available participants first, follow-up with busy participants',
            'schedule_all_with_reschedule': 'All participants scheduled with low-priority meeting rescheduled'
        }
        
        return strategy_map.get(action, 'Standard scheduling')
    
    def format_test_case_output(self, test_case_number, resolution_result):
        """Format output for specific test cases"""
        
        if test_case_number == 1:
            # Test Case 1: All available
            return {
                "status": "success",
                "message": "Meeting scheduled successfully with all participants",
                "scheduled_time": resolution_result['recommended_time'],
                "participants": resolution_result['participants_to_include']
            }
        
        elif test_case_number == 2:
            # Test Case 2: One busy with low priority
            return {
                "status": "partial_success",
                "message": "Meeting scheduled with organizer first, follow-up with busy participant",
                "primary_meeting": {
                    "time": resolution_result['recommended_time'],
                    "participants": resolution_result['participants_to_include']
                },
                "follow_up_required": resolution_result.get('follow_up_meetings', [])
            }
        
        elif test_case_number == 3:
            # Test Case 3: All busy
            return {
                "status": "rescheduled",
                "message": "All participants busy - rescheduled to tomorrow",
                "new_time": resolution_result['recommended_time'],
                "participants": resolution_result['participants_to_include']
            }
        
        elif test_case_number == 4:
            # Test Case 4: One free, one busy but not critical
            return {
                "status": "partial_success",
                "message": "Meeting scheduled with available participants only",
                "scheduled_time": resolution_result['recommended_time'],
                "included_participants": resolution_result['participants_to_include'],
                "excluded_participants": resolution_result.get('follow_up_needed', [])
            }
        
        else:
            return resolution_result
