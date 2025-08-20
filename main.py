# main.py - TikLeapスクレイピング（CSV出力版）
import os
import logging
import time
import random
import requests
import csv
import io
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, Response, render_template_string

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# HTMLテンプレート（入力フォーム）
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>TikLeap Scraper</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        textarea {
            width: 100%;
            height: 200px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            font-family: monospace;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .info {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: #f0f8ff;
            border-radius: 5px;
            display: none;
        }
        .error {
            color: red;
            margin-top: 10px;
        }
        .success {
            color: green;
            margin-top: 10px;
        }
        #loading {
            display: none;
            margin-top: 20px;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4CAF50;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 TikLeap スクレイピングツール</h1>
        
        <div class="info">
            <strong>使い方：</strong><br>
            1. ユーザーIDを1行に1つずつ入力してください<br>
            2. 「スクレイピング開始」をクリック<br>
            3. 処理完了後、CSVファイルがダウンロードされます
        </div>
        
        <form id="scraperForm">
            <label for="userIds"><strong>ユーザーIDリスト：</strong></label><br>
            <textarea id="userIds" name="userIds" placeholder="例：&#10;setsu_dayo&#10;user123&#10;example_user">setsu_dayo</textarea><br>
            
            <button type="submit" id="submitBtn">🚀 スクレイピング開始</button>
        </form>
        
        <div id="loading">
            <div class="spinner"></div>
            <span>処理中... しばらくお待ちください</span>
        </div>
        
        <div id="result" class="result"></div>
    </div>
    
    <script>
        document.getElementById('scraperForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const userIds = document.getElementById('userIds').value;
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const resultDiv = document.getElementById('result');
            
            if (!userIds.trim()) {
                alert('ユーザーIDを入力してください');
                return;
            }
            
            submitBtn.disabled = true;
            loading.style.display = 'block';
            resultDiv.style.display = 'none';
            
            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_ids: userIds.split('\\n').filter(id => id.trim())
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `tikleap_data_${new Date().toISOString().split('T')[0]}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    resultDiv.innerHTML = '<div class="success">✅ CSVファイルのダウンロードが完了しました！</div>';
                    resultDiv.style.display = 'block';
                } else {
                    const error = await response.json();
                    resultDiv.innerHTML = `<div class="error">❌ エラー: ${error.error}</div>`;
                    resultDiv.style.display = 'block';
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="error">❌ エラー: ${error.message}</div>`;
                resultDiv.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

class TikLeapScraper:
    def __init__(self):
        """TikLeapスクレイピングシステム（スタンドアロン版）"""
        # HTTPセッション初期化
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        })
        logger.info("✅ TikLeapScraperシステム初期化完了")
    
    def scrape_tikleap_profile(self, user_id):
        """TikLeapプロフィールページから収益データを取得"""
        url = f"https://www.tikleap.com/profile/{user_id}"
        
        try:
            logger.info(f"🔍 スクレイピング開始: {url}")
            
            # リクエスト間隔の調整
            time.sleep(random.uniform(1.0, 2.0))
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # profile-earning-buttonクラスのspanタグを探す
            earning_element = soup.find('span', class_='profile-earning-button')
            
            if earning_element:
                earning_value = earning_element.get_text().strip()
                logger.info(f"✅ {user_id}: 収益データ = {earning_value}")
                return {
                    'user_id': user_id,
                    'diamond': earning_value,
                    'status': 'success',
                    'error': None,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                logger.warning(f"⚠️ {user_id}: データ要素が見つかりません")
                return {
                    'user_id': user_id,
                    'diamond': None,
                    'status': 'not_found',
                    'error': 'Element not found',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
        except requests.RequestException as e:
            logger.error(f"❌ {user_id} ネットワークエラー: {e}")
            return {
                'user_id': user_id,
                'diamond': None,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"❌ {user_id} 処理エラー: {e}")
            return {
                'user_id': user_id,
                'diamond': None,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def scrape_multiple_users(self, user_ids):
        """複数ユーザーのデータを取得"""
        results = []
        total = len(user_ids)
        
        for i, user_id in enumerate(user_ids, 1):
            logger.info(f"📊 処理中 {i}/{total}: {user_id}")
            result = self.scrape_tikleap_profile(user_id)
            results.append(result)
        
        return results
    
    def generate_csv(self, results):
        """結果をCSV形式で生成"""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['user_id', 'diamond', 'status', 'error', 'timestamp'],
            quoting=csv.QUOTE_MINIMAL
        )
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
        
        return output.getvalue()

# Flask アプリケーション
app = Flask(__name__)
scraper = TikLeapScraper()

@app.route('/')
def home():
    """Webインターフェース"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
def scrape():
    """スクレイピング実行とCSV返却"""
    try:
        data = request.json
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'error': 'No user IDs provided'}), 400
        
        # スクレイピング実行
        results = scraper.scrape_multiple_users(user_ids)
        
        # CSV生成
        csv_data = scraper.generate_csv(results)
        
        # CSVファイルとして返却
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=tikleap_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"❌ エラー: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape', methods=['GET'])
def api_scrape():
    """API版：単一ユーザースクレイピング"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id parameter is required'}), 400
    
    result = scraper.scrape_tikleap_profile(user_id)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🌐 サーバー起動: ポート{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
