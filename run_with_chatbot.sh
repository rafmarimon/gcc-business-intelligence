#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Check if we have an argument to skip collection
SKIP_COLLECTION=""
NO_BROWSER=""

for arg in "$@"
do
    if [ "$arg" == "--skip-collection" ]; then
        SKIP_COLLECTION="--skip-collection"
    fi
    if [ "$arg" == "--no-browser" ]; then
        NO_BROWSER="--no-browser"
    fi
done

# Start the Flask API server in the background
echo "Starting API server..."
python src/api_server.py &
API_PID=$!

# Give the API server a moment to start
sleep 2

# Run the report generation
echo "Generating report..."
python src/manual_run.py $SKIP_COLLECTION $NO_BROWSER

# Instructions for the user
echo ""
echo "======================================================================================"
echo "✅ API Server is running in the background (PID: $API_PID)"
echo "📊 Your report has been generated with chatbot functionality enabled"
echo "❓ The chatbot can answer questions about the report content and GCC business trends"
echo "⚠️ To stop the API server, run: kill $API_PID"
echo "======================================================================================"

# Keep the script running to maintain the API server
echo "Press Ctrl+C to quit and stop the API server..."
wait $API_PID 