# main.py - TikLeapスクレイピング（アンチボット対策版）
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
        .warning {
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #ffc107;
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
        .test-section {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 TikLeap スクレイピングツール</h1>
        
        <div class="warning">
            <strong>⚠️ 注意：</strong><br>
            TikLeapは403エラーを返す場合があります。<br>
            その場合は、以下の代替方法をお試しください：<br>
            1. 少し時間を置いてから再試行<br>
            2. 1つずつユーザーIDをテスト<br>
            3. 手動でブラウザからアクセス可能か確認
        </div>
        
        <div class="info">
            <strong>使い方：</strong><br>
            1. ユーザーIDを1行に1つずつ入力してください<br>
            2. 「スクレイピング開始」をクリック<br>
            3. 処理完了後、CSVファイルがダウンロードされます
        </div>
        
        <form id="scraperForm">
            <label for="userIds"><strong>ユーザーIDリスト：</strong></label><br>
            <textarea id="userIds" name="userIds" placeholder="例：&#10;setsu_dayo&#10;user123&#10;example_user">setsu_dayo
kururi_kore
pukudayo24</textarea><br>
            
            <button type="submit" id="submitBtn">🚀 スクレイピング開始（ゆっくり処理）</button>
        </form>
        
        <div id="loading">
            <div class="spinner"></div>
            <span>処理中... 各ユーザー3-5秒待機しています</span>
        </div>
        
        <div id="result" class="result"></div>
        
        <div class="test-section">
            <h3>🧪 単一ユーザーテスト</h3>
            <input type="text" id="testUserId" placeholder="テストするユーザーID" style="padding: 8px; width: 200px;">
            <button onclick="testSingleUser()" style="padding: 8px 20px;">テスト実行</button>
            <div id="testResult" style="margin-top: 10px;"></div>
        </div>
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
        
        async function testSingleUser() {
            const userId = document.getElementById('testUserId').value;
            const resultDiv = document.getElementById('testResult');
            
            if (!userId) {
                alert('ユーザーIDを入力してください');
                return;
            }
            
            resultDiv.innerHTML = '🔄 テスト中...';
            
            try {
                const response = await fetch(`/api/scrape?user_id=${userId}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    resultDiv.innerHTML = `✅ 成功: Diamond = ${data.diamond}`;
                } else {
                    resultDiv.innerHTML = `❌ エラー: ${data.error}`;
                }
            } catch (error) {
                resultDiv.innerHTML = `❌ エラー: ${error.message}`;
            }
        }
    </script>
</body>
</html>
"""

class TikLeapScraper:
    def __init__(self):
        """TikLeapスクレイピングシステム（アンチボット対策版）"""
        # ユーザーエージェントのリスト（ランダムに選択）
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        # セッションは毎回新しく作成
        logger.info("✅ TikLeapScraperシステム初期化完了")
    
    def create_session(self):
        """新しいセッションを作成（毎回異なるヘッダー）"""
        session = requests.Session()
        
        # ランダムなユーザーエージェントを選択
        user_agent = random.choice(self.user_agents)
        
        # より本物のブラウザに近いヘッダー
        session.headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        return session
    
    def scrape_tikleap_profile(self, user_id, retry_count=3):
        """TikLeapプロフィールページから収益データを取得（リトライ機能付き）"""
        url = f"https://www.tikleap.com/profile/{user_id}"
        
        for attempt in range(retry_count):
            try:
                # 各試行で新しいセッションを使用
                session = self.create_session()
                
                logger.info(f"🔍 スクレイピング開始 (試行 {attempt + 1}/{retry_count}): {url}")
                
                # より長いランダムな待機時間
                wait_time = random.uniform(3.0, 5.0) + (attempt * 2)  # リトライごとに待機時間を増やす
                logger.info(f"⏳ {wait_time:.1f}秒待機中...")
                time.sleep(wait_time)
                
                # リクエスト送信
                response = session.get(
                    url, 
                    timeout=20,
                    allow_redirects=True,
                    verify=True
                )
                
                logger.info(f"📡 ステータスコード: {response.status_code}")
                
                # 403エラーの場合、リトライ
                if response.status_code == 403:
                    logger.warning(f"⚠️ 403 Forbidden - 試行 {attempt + 1}/{retry_count}")
                    if attempt < retry_count - 1:
                        continue
                    else:
                        return {
                            'user_id': user_id,
                            'diamond': None,
                            'status': 'blocked',
                            'error': '403 Forbidden - Access blocked by server',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                
                response.raise_for_status()
                
                # HTMLパース
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # デバッグ: HTMLの一部を出力
                logger.info(f"📄 HTML長さ: {len(response.content)} bytes")
                
                # 複数の方法でデータを探す
                earning_value = None
                
                # 方法1: profile-earning-buttonクラス
                earning_element = soup.find('span', class_='profile-earning-button')
                if earning_element:
                    earning_value = earning_element.get_text().strip()
                    logger.info(f"✅ 方法1で取得: {earning_value}")
                
                # 方法2: 他の可能性のあるセレクター
                if not earning_value:
                    # profile-earningを含むクラス
                    earning_elements = soup.find_all('span', class_=lambda x: x and 'earning' in x.lower() if x else False)
                    if earning_elements:
                        earning_value = earning_elements[0].get_text().strip()
                        logger.info(f"✅ 方法2で取得: {earning_value}")
                
                # 方法3: データ属性を探す
                if not earning_value:
                    data_elements = soup.find_all(['span', 'div'], attrs={'data-earning': True})
                    if data_elements:
                        earning_value = data_elements[0].get_text().strip()
                        logger.info(f"✅ 方法3で取得: {earning_value}")
                
                if earning_value:
                    logger.info(f"✅ {user_id}: 収益データ = {earning_value}")
                    return {
                        'user_id': user_id,
                        'diamond': earning_value,
                        'status': 'success',
                        'error': None,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    # HTMLの一部をログに出力してデバッグ
                    all_spans = soup.find_all('span', class_=True)[:10]
                    logger.warning(f"⚠️ データ要素が見つかりません。見つかったspan: {[span.get('class') for span in all_spans]}")
                    
                    return {
                        'user_id': user_id,
                        'diamond': None,
                        'status': 'not_found',
                        'error': 'Data element not found in HTML',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                
            except requests.exceptions.HTTPError as e:
                if '403' in str(e):
                    logger.error(f"❌ {user_id} 403エラー (試行 {attempt + 1}/{retry_count}): {e}")
                    if attempt < retry_count - 1:
                        continue
                else:
                    logger.error(f"❌ {user_id} HTTPエラー: {e}")
                    return {
                        'user_id': user_id,
                        'diamond': None,
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            except requests.RequestException as e:
                logger.error(f"❌ {user_id} ネットワークエラー (試行 {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    continue
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
            finally:
                # セッションをクローズ
                if 'session' in locals():
                    session.close()
        
        # 全てのリトライが失敗
        return {
            'user_id': user_id,
            'diamond': None,
            'status': 'failed',
            'error': f'Failed after {retry_count} attempts',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def scrape_multiple_users(self, user_ids):
        """複数ユーザーのデータを取得"""
        results = []
        total = len(user_ids)
        
        for i, user_id in enumerate(user_ids, 1):
            logger.info(f"📊 処理中 {i}/{total}: {user_id}")
            result = self.scrape_tikleap_profile(user_id.strip())
            results.append(result)
            
            # 最後のユーザー以外は追加の待機
            if i < total:
                wait_time = random.uniform(2.0, 4.0)
                logger.info(f"⏳ 次のユーザーまで{wait_time:.1f}秒待機...")
                time.sleep(wait_time)
        
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

@app.route('/debug', methods=['GET'])
def debug_page():
    """デバッグ用：実際のHTMLを確認"""
    user_id = request.args.get('user_id', 'setsu_dayo')
    url = f"https://www.tikleap.com/profile/{user_id}"
    
    try:
        session = scraper.create_session()
        response = session.get(url, timeout=20)
        
        return f"""
        <h1>Debug Info for {user_id}</h1>
        <p>URL: {url}</p>
        <p>Status Code: {response.status_code}</p>
        <p>Headers: {dict(response.headers)}</p>
        <hr>
        <h2>HTML Preview (first 5000 chars):</h2>
        <pre>{response.text[:5000]}</pre>
        """
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🌐 サーバー起動: ポート{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
