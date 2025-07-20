from flask import Flask, request, jsonify
from threading import Thread
import json
import sys
import os

from meeting_assistant import your_meeting_assistant

app = Flask(__name__)
received_data = []

@app.route('/receive', methods=['POST'])
def receive():
    try:
        data = request.get_json()
        print(f"\\n=== Received Meeting Request ===")
        print(f"{json.dumps(data, indent=2)}")
        # Process the meeting request using AI assistant
        response_data = your_meeting_assistant(data)
        # Store for debugging
        received_data.append(data)
        
        print(f"\\n=== Sending Response ===")
        print(f"{json.dumps(response_data, indent=2)}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        error_response = {
            "Request_id": data.get("Request_id", "") if 'data' in locals() else "",
            "error": str(e),
            "status": "failed"
        }
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "AI Meeting Assistant is running"})

@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to see received requests"""
    return jsonify({
        "received_requests": len(received_data),
        "last_requests": received_data[-5:] if received_data else []
    })

def run_flask():
    """Run the Flask server"""
    print("\\n=== Starting AI Meeting Assistant Server ===")
    print("Server will run on http://0.0.0.0:5000")
    print("Endpoints:")
    print("  POST /receive - Process meeting requests")
    print("  GET /health - Health check")
    print("  GET /debug - Debug information")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    # Start Flask server
    run_flask()
else:
    # Start Flask in a background thread when imported
    print("Starting AI Meeting Assistant in background...")
    Thread(target=run_flask, daemon=True).start()
