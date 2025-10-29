try:
    from flask import Flask, request
    from main import main as run_notifications
    from logger import setup_logging
except Exception as e:
    print(f"Failed to import within cron.py: {str(e)}")

try:

    app = Flask(__name__)
    logger = setup_logging(__name__)

except Exception as e:
    print(f"Failed to startup Flask App or logger: {str(e)}")

@app.route("/", methods=['POST', 'GET', 'OPTIONS'])
def trigger_notifications():
    '''
    Endpoint for the cloud scheduler
    'POST' or 'GET' method. 

    Runs the main.py files as run_notifications

    '''
    try:
        logger.info("Notification cron job triggered")
        run_notifications()
        return "Notifications completed successfully", 200
    
    except Exception as e:
        logger.error(f"Error triggering notification cron job: {str(e)}")
        return f"Error triggering notification cron job: {str(e)}", 

if __name__ == '__main__':
    import os

    #For local testing
    if os.environ.get('FLASK_ENV') != 'production':
        port = int(os.environ.get('PORT', 5000))
        app.run(host='127.0.0.1', port=port, debug=True)

    else:
        pass