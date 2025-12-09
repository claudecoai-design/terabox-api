from flask import Flask, request, jsonify
import requests
import re
import json
from urllib.parse import quote, unquote

app = Flask(__name__)

class TeraboxDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.terabox.com',
            'Referer': 'https://www.terabox.com/',
        }
    
    def extract_surl(self, url):
        """Extract surl from Terabox URL"""
        patterns = [
            r'/s/([a-zA-Z0-9_-]+)',
            r'surl=([a-zA-Z0-9_-]+)',
            r'/wap/share/file\?surl=([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_file_info(self, url):
        """Get file information from Terabox"""
        try:
            surl = self.extract_surl(url)
            if not surl:
                return {'success': False, 'message': 'Invalid Terabox URL'}
            
            # Terabox list API
            api_url = 'https://www.terabox.com/share/list'
            
            params = {
                'shorturl': surl,
                'root': '1',
                'page': '1',
                'num': '20',
                'order': 'time',
                'desc': '1',
                'web': '1',
                'channel': 'dubox',
                'clienttype': '0',
                'jsToken': self._get_js_token(surl)
            }
            
            response = requests.get(api_url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('errno') == 0:
                    file_list = data.get('list', [])
                    
                    if file_list:
                        file_data = file_list[0]
                        
                        # Get download link
                        download_url = self._get_download_url(file_data, surl)
                        
                        return {
                            'success': True,
                            'data': {
                                'filename': file_data.get('server_filename', 'Unknown'),
                                'size': file_data.get('size', 0),
                                'fs_id': file_data.get('fs_id'),
                                'download_url': download_url,
                                'thumbnail': file_data.get('thumbs', {}).get('url3', ''),
                                'category': file_data.get('category', 0),
                                'isdir': file_data.get('isdir', 0)
                            }
                        }
                    else:
                        return {'success': False, 'message': 'No files found in the link'}
                else:
                    return {'success': False, 'message': f"Terabox API Error: {data.get('errno')}"}
            
            return {'success': False, 'message': 'Failed to fetch data from Terabox'}
        
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def _get_js_token(self, surl):
        """Generate JS Token (simplified)"""
        # This is a basic implementation
        # Terabox uses complex token generation
        return 'undefined'
    
    def _get_download_url(self, file_data, surl):
        """Generate download URL"""
        try:
            fs_id = file_data.get('fs_id')
            server_filename = file_data.get('server_filename', 'file')
            
            # Terabox download API
            download_api = 'https://www.terabox.com/share/download'
            
            params = {
                'surl': surl,
                'fid_list': f'[{fs_id}]',
                'channel': 'dubox',
                'clienttype': '0',
                'web': '1',
                'app_id': '250528'
            }
            
            response = requests.get(
                download_api, 
                params=params, 
                headers=self.headers,
                allow_redirects=False,
                timeout=30
            )
            
            if response.status_code in [302, 301]:
                # Got redirect location
                return response.headers.get('Location', '')
            
            # Try to extract from response
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('errno') == 0:
                        dlink = data.get('dlink', '')
                        if dlink:
                            return dlink
                except:
                    pass
            
            # Fallback: construct direct link
            return f"https://www.terabox.com/share/download?surl={surl}&fid_list=[{fs_id}]"
        
        except Exception as e:
            print(f"Download URL error: {e}")
            return f"https://www.terabox.com/sharing/link?surl={surl}"

# Initialize downloader
downloader = TeraboxDownloader()

@app.route('/')
def home():
    """API Home"""
    return jsonify({
        'name': 'Terabox Downloader API',
        'version': '1.0',
        'developer': 'Shohan',
        'endpoints': {
            'download': '/api/download',
            'info': '/api/info'
        },
        'usage': {
            'method': 'POST',
            'body': {'url': 'https://terabox.com/s/xxxxx'}
        }
    })

@app.route('/api/download', methods=['POST', 'GET'])
def download():
    """Download endpoint"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            url = data.get('url')
        else:
            url = request.args.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'message': 'URL parameter is required'
            }), 400
        
        result = downloader.get_file_info(url)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/info', methods=['POST', 'GET'])
def info():
    """Get file info only"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            url = data.get('url')
        else:
            url = request.args.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'message': 'URL parameter is required'
            }), 400
        
        result = downloader.get_file_info(url)
        
        # Remove download URL for info endpoint
        if result.get('success') and 'data' in result:
            result['data'].pop('download_url', None)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'API is running'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
