import sys
import os

# Add the parent directory to the path to import our Flask app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import app

def handler(event, context):
    """
    Netlify serverless function handler for Flask app
    """
    try:
        # Import the serverless WSGI handler
        from werkzeug.serving import WSGIRequestHandler
        from werkzeug.wrappers import Request, Response
        import json
        
        # Extract request details from Netlify event
        path = event.get('path', '/')
        method = event.get('httpMethod', 'GET')
        headers = event.get('headers', {})
        query_string = event.get('queryStringParameters') or {}
        body = event.get('body', '')
        
        # Convert query parameters to query string format
        query_string_formatted = '&'.join([f"{k}={v}" for k, v in query_string.items()])
        
        # Create a WSGI environ dict
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': query_string_formatted,
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)) if body else '0',
            'SERVER_NAME': headers.get('host', 'localhost'),
            'SERVER_PORT': '443',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': body,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add headers to environ
        for key, value in headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
            environ[key] = value
        
        # Use Flask's test client to handle the request
        with app.test_client() as client:
            if method == 'GET':
                response = client.get(path, query_string=query_string_formatted, headers=headers)
            elif method == 'POST':
                response = client.post(path, data=body, headers=headers, query_string=query_string_formatted)
            elif method == 'PUT':
                response = client.put(path, data=body, headers=headers, query_string=query_string_formatted)
            elif method == 'DELETE':
                response = client.delete(path, headers=headers, query_string=query_string_formatted)
            else:
                response = client.open(path, method=method, data=body, headers=headers, query_string=query_string_formatted)
            
            # Convert Flask response to Netlify response format
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': response.get_data(as_text=True),
                'isBase64Encoded': False
            }
            
    except Exception as e:
        print(f"Error in serverless function: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)}),
            'isBase64Encoded': False
        }