from flask import Flask, jsonify
import requests
from datetime import datetime
import time

app = Flask(__name__)

# Simple rate limiting
last_requests = []

def rate_limit():
    global last_requests
    now = time.time()
    last_requests = [req_time for req_time in last_requests if now - req_time < 10]
    
    if len(last_requests) >= 85:
        return False
    
    last_requests.append(now)
    return True

@app.route('/jewish-info', methods=['GET'])
def get_jewish_info():
    """Get current Hebrew date and Torah portion"""
    if not rate_limit():
        return jsonify({
            'error': 'Please try again in a moment.',
            'success': False
        }), 429
    
    try:
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        # Get data from Hebcal with more options to ensure Hebrew dates
        params = {
            'v': '1',
            'cfg': 'json',
            's': 'on',  # Torah readings
            'maj': 'on',  # Major holidays
            'min': 'on',  # Minor holidays
            'nx': 'on',   # Rosh Chodesh (this often has Hebrew dates)
            'year': now.year,
            'month': now.month
        }
        
        response = requests.get('https://www.hebcal.com/hebcal', params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Find current parsha and Hebrew date
        parsha = "Parsha information not available"
        hebrew_date = None
        
        # Look through events
        for event in data.get('items', []):
            event_date = event.get('date', '')
            event_title = event.get('title', '')
            event_hdate = event.get('hdate', '')
            
            # Get Hebrew date from any event close to today
            if event_date and event_hdate:
                event_date_obj = datetime.strptime(event_date, '%Y-%m-%d')
                days_diff = abs((event_date_obj - now).days)
                if days_diff <= 2:  # Within 2 days
                    hebrew_date = event_hdate
            
            # Get current week's parsha
            if 'parashat' in event_title.lower() or 'parashah' in event_title.lower():
                event_date_obj = datetime.strptime(event_date, '%Y-%m-%d')
                days_diff = (event_date_obj - now).days
                if -7 <= days_diff <= 7:  # Within this week
                    parsha = event_title
        
        # If we still don't have Hebrew date, try a different approach
        if not hebrew_date:
            # Try to get more events around today
            yesterday = now.replace(day=now.day-1) if now.day > 1 else now
            tomorrow = now.replace(day=now.day+1) if now.day < 28 else now
            
            for single_day in [yesterday, now, tomorrow]:
                day_params = {
                    'v': '1',
                    'cfg': 'json',
                    'maj': 'on',
                    'min': 'on',
                    'nx': 'on',
                    'mf': 'on',  # Add minor fasts
                    'ss': 'on',  # Add special Shabbatot
                    'year': single_day.year,
                    'month': single_day.month,
                    'day': single_day.day
                }
                
                try:
                    day_response = requests.get('https://www.hebcal.com/hebcal', params=day_params, timeout=5)
                    day_data = day_response.json()
                    
                    for event in day_data.get('items', []):
                        if event.get('hdate'):
                            hebrew_date = event.get('hdate')
                            break
                    
                    if hebrew_date:
                        break
                except:
                    continue
        
        return jsonify({
            'success': True,
            'hebrew_date': hebrew_date or 'Hebrew date not available',
            'parsha': parsha,
            'gregorian_date': today_str
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Unable to get Jewish calendar information',
            'hebrew_date': 'Not available',
            'parsha': 'Not available'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
