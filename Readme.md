# AMD-Scheduling_Assistant
Hackathon Organized at IISC Bangalore By AMD

## 🏗️ Architecture

The system is built with a modular architecture:

```
AI_Scheduler_Complete/
├── meeting_assistant.py     # Main orchestrator
├── ai_agent.py              # AI parsing and conflict resolution
├── calendar_utils.py        # Google Calendar integration
├── conflict_resolver.py     # Intelligent conflict resolution
├── output_formatter.py      # Response formatting
├── submission_complete.py   # Flask server
├── run.ipynb                # main running file
├──Cred_to_Token.ipynb       # Google Calendar authentication
└── README.md                # This file

```
FLow diagram:
1. CLIENT REQUEST
   ├── run.ipynb / run.ipynb
   ├── Loads: sample_request.json
   └── POST → http://localhost:5000/receive

2. FLASK SERVER ENTRY
   ├── submission_complete.py
   ├── Route: /receive
   └── Calls: your_meeting_assistant(data)

3. MAIN ORCHESTRATOR
   ├── meeting_assistant.py
   ├── Function: your_meeting_assistant()
   └── Coordinates entire flow

4. AI PARSING PHASE
   ├── ai_agent.py
   ├── Function: parse_meeting_request()
   ├── Calls: meta llama model (port 3000)
   └── Extracts: participants, duration, time_constraint

5. WEEKEND VALIDATION
   ├── calendar_utils.py
   ├── Function: get_date_range_from_constraint()
   └── Check: If weekend → Raise exception

6. CALENDAR RETRIEVAL
   ├── calendar_utils.py
   ├── Function: retrieve_calendar_events()
   ├── Loops: For each participant
   └── Gets: Existing calendar events

7. CONFLICT ANALYSIS
   ├── conflict_resolver.py
   ├── Function: resolve_conflicts()
   ├── Analyzes: All participants' availability
   └── Applies: Test case logic

8. DECISION ENGINE
   ├── conflict_resolver.py
   ├── Functions: Various test case handlers
   ├── Logic: Importance-based scheduling
   └── Returns: Optimal meeting time

9. RESPONSE FORMATTING
   ├── output_formatter.py
   ├── Function: format_output()
   ├── Template: Output_Event.json format
   └── Creates: Final JSON response

10. RESPONSE DELIVERY
    ├── submission_complete.py
    ├── Returns: JSON to client
    └── Client displays result

##  Quick Start

### 1. Start the AI Server
First, make sure your vLLM server is running (meta-llama model on port 3000):
```bash
# In your vLLM environment
HIP_VISIBLE_DEVICES=0 vllm serve /home/user/Models/meta-llama/Meta-Llama-3.1-8B-Instruct \
        --gpu-memory-utilization 0.3 \
        --swap-space 16 \
        --disable-log-requests \
        --dtype float16 \
        --max-model-len 2048 \
        --tensor-parallel-size 1 \
        --host 0.0.0.0 \
        --port 4000 \
        --num-scheduler-steps 10 \
        --max-num-seqs 128 \
        --max-num-batched-tokens 2048 \
        --max-model-len 2048 \
        --distributed-executor-backend "mp"```

### 2. Start the Meeting Assistant Server
```bash
# Run the server
python submission_complete.py
```

The server will start on `http://localhost:5000` with endpoints:
- `POST /receive` - Process meeting requests
- `GET /health` - Health check
- `GET /debug` - Debug information

### 3. Test the System
```bash
for running the Program use run.ipynb and upload the input file from Json_Samples folder
```

## Meta LLama Model-Powered Features

### 1. **Intelligent Email Parsing**
- Extracts participants, duration, time constraints, and subject
- Handles natural language variations
- Auto-completes email domains (@amd.com)

### 2. **Smart Conflict Resolution**
- **Test Case 1**: All available → Direct scheduling
- **Test Case 2**: Urgent meeting with conflicts → Partial scheduling with follow-up
- **Test Case 3**: All busy → Reschedule to tomorrow
- **Test Case 4**: Non-critical participant busy → Proceed with available participants

### 3. **Calendar Integration**
- Real-time Google Calendar access
- Multi-participant availability checking
- Free slot detection within business hours

### 4. **Priority-Based Decisions**
- Meeting importance analysis based on subject keywords
- Intelligent rescheduling of low-priority conflicts
- Context-aware participant inclusion/exclusion

### 5. **Weekend Protection**
- **Automatic rejection** of Saturday/Sunday meeting requests
- **Clear messaging**: "Its weekends no meetings are possible"
- **Business hours enforcement**: Meetings only scheduled Monday-Friday

##  Test Cases Coverage

| Test Case | Scenario | AI Decision | Expected Outcome |
|-----------|----------|-------------|------------------|
| **Case 1** | All participants free | Schedule all |  Direct scheduling |
| **Case 2** | Urgent + one busy | Partial schedule |  Organizer first, follow-up |
| **Case 3** | All busy (important) | Reschedule tomorrow |  Next day scheduling |
| **Case 4** | Feedback + one busy | Schedule available | Proceed with subset |
| **Case 5** | Saturday meeting | Reject weekend | "Its weekends no meetings are possible" |
| **Case 6** | Sunday meeting | Reject weekend | "Its weekends no meetings are possible" |

## 🔧 Configuration

### AI Model Settings
- **Model**: meta-llama
- **Temperature**: 0.0 (deterministic)
- **Context**: Meeting-specific prompts
- **Fallback**: Manual parsing if AI unavailable

### Calendar Settings
- **Working Hours**: 9 AM - 6 PM IST
- **Time Zone**: +05:30 (IST)
- **Minimum Duration**: 15 minutes
- **Default Duration**: 30 minutes

### Conflict Resolution Rules
1. **All Available**: Schedule immediately
2. **Partial Conflicts**: 
   - Urgent meetings → Partial scheduling
   - Regular meetings → Find alternatives
3. **All Busy**: Reschedule to next available day
4. **Priority Override**: High-priority meetings can reschedule low-priority ones
5. **Weekend Protection**: Automatically reject Saturday/Sunday requests

### Request Format
```json
{
    "Request_id": "unique-id",
    "Datetime": "19-07-2025T12:34:55",
    "Location": "IISc Bangalore",
    "From": "organizer@amd.com",
    "Attendees": [
        {"email": "participant1@amd.com"},
        {"email": "participant2@amd.com"}
    ],
    "Subject": "Meeting Subject",
    "EmailContent": "Natural language meeting request..."
}
```

### Response Format
```json
{
    "Request_id": "unique-id",
    "EventStart": "2025-07-24T10:30:00+05:30",
    "EventEnd": "2025-07-24T11:00:00+05:30",
    "Duration_mins": "30",
    "Attendees": [...],
    "MetaData": {
        "resolution_action": "schedule_all",
        "resolution_reason": "All participants available",
        "scheduling_strategy": "Direct scheduling"
    }
}
```

##  Debugging

### Server Logs
The server provides detailed logging:
- Request parsing results
- Calendar access status
- AI decision reasoning
- Final scheduling outcome

### Health Monitoring
```bash
curl http://localhost:5000/health
curl http://localhost:5000/debug
```

### Common Issues
1. **AI Model Not Available**: System falls back to manual parsing
2. **Calendar Access Failed**: Assumes participant is available
3. **Parsing Errors**: Uses default values (30 min duration, flexible timing)

##  Key Algorithms

### Conflict Resolution Logic
```python
if all_participants_available:
    schedule_immediately()
elif urgent_meeting and some_available:
    schedule_partial_with_followup()
elif all_busy_with_low_priority:
    reschedule_conflicts_and_proceed()
else:
    reschedule_to_tomorrow()
```

### Time Slot Finding
```python
def find_optimal_slot(constraints, duration, participant_events):
    # 1. Parse time constraints (Thursday, Monday 9 AM, etc.)
    # 2. Check participant availability
    # 3. Find common free slots
    # 4. Apply business hour constraints
    # 5. Return optimal time
```

