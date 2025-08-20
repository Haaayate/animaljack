# main.py - TikLeapスクレイピング＆スプレッドシート更新システム
import os
import json
import logging
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TikLeapScraper:
    def __init__(self):
        """
        TikLeapスクレイピング＆Googleスプレッドシート更新システム
        """
        # スプレッドシートID（直接指定）
        self.spreadsheet_id = "1VuNZSEl2aP0_kmQkxDLxYM3YzC2qXRAZD-dH8XGO-g0"
        
        # 環境変数から認証情報を取得
        self.credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if not self.credentials_json:
            logger.error("GOOGLE_CREDENTIALS_JSON environment variable is not set")
            raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable is required")
        
        # Google Sheets API初期化
        self.sheets_service = None
        self._init_google_sheets()
        
        # HTTPセッション初期化（スクレイピング用）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("✅ TikLeapScraperシステム初期化完了")
    
    def _init_google_sheets(self):
        """Google Sheets API認証とサービス初期化"""
        try:
            # JSON文字列からクレデンシャルを作成
            credentials_info = json.loads(self.credentials_json)
            
            # サービスアカウント認証
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets'  # 読み書き権限
                ]
            )
            
            # Sheets APIサービスを構築
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            logger.info("✅ Google Sheets API認証成功")
            
            # 接続テスト
            self._test_connection()
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 認証情報のJSON解析エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Google Sheets API初期化エラー: {e}")
            raise
    
    def _test_connection(self):
        """スプレッドシートへの接続をテスト"""
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            title = spreadsheet.get('properties', {}).get('title', 'Unknown')
            logger.info(f"📊 接続成功: スプレッドシート '{title}'")
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.error(f"❌ スプレッドシートが見つかりません: {self.spreadsheet_id}")
            elif e.resp.status == 403:
                logger.error(f"❌ スプレッドシートへのアクセス権限がありません")
            else:
                logger.error(f"❌ 接続テストエラー: {e}")
            raise
    
    def get_user_ids_from_sheet(self):
        """スプレッドシートのA列からユーザーIDを取得（A2から開始）"""
        try:
            # A2から下のデータを取得
            range_name = 'A2:A'
            logger.info(f"📋 範囲 '{range_name}' からデータ取得中...")
            
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("⚠️ A2以降にデータがありません")
                return []
            
            # ユーザーIDリストを作成
            user_ids = []
            for i, row in enumerate(values, start=2):  # A2から始まるので行番号は2から
                if row and row[0] and row[0].strip():  # 空でない値のみ
                    user_id = row[0].strip()
                    user_ids.append({
                        'row_number': i,  # スプレッドシートの実際の行番号
                        'user_id': user_id
                    })
                    logger.info(f"  行{i}: {user_id}")
            
            logger.info(f"✅ {len(user_ids)}個のユーザーIDを取得しました")
            return user_ids
            
        except HttpError as e:
            logger.error(f"❌ スプレッドシート読み取りエラー: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ データ取得エラー: {e}")
            return []
    
    def scrape_tikleap_profile(self, user_id):
        """TikLeapプロフィールページから収益データを取得"""
        url = f"https://www.tikleap.com/profile/{user_id}"
        
        try:
            logger.info(f"🔍 スクレイピング開始: {url}")
            
            # リクエスト間隔の調整（サーバー負荷軽減）
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
                    'success': True,
                    'value': earning_value,
                    'raw_html': str(earning_element)[:200]  # デバッグ用
                }
            else:
                # 別の可能性のあるセレクターも試す
                logger.warning(f"⚠️ {user_id}: profile-earning-buttonクラスが見つかりません")
                
                # デバッグ情報を出力
                all_spans = soup.find_all('span', class_=True)
                logger.info(f"  見つかったspanタグのクラス: {[span.get('class') for span in all_spans[:10]]}")
                
                return {
                    'success': False,
                    'value': None,
                    'error': 'Element not found'
                }
            
        except requests.RequestException as e:
            logger.error(f"❌ {user_id} ネットワークエラー: {e}")
            return {
                'success': False,
                'value': None,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ {user_id} 処理エラー: {e}")
            return {
                'success': False,
                'value': None,
                'error': f'Processing error: {str(e)}'
            }
    
    def update_diamond_value(self, row_number, value):
        """スプレッドシートのD列（diamond）に値を更新"""
        try:
            # D列の該当行に値を書き込む
            range_name = f'D{row_number}'
            
            body = {
                'values': [[value if value else 'N/A']]
            }
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # 数値は数値として、文字列は文字列として解釈
                body=body
            ).execute()
            
            logger.info(f"📝 行{row_number}のD列を更新: {value}")
            return True
            
        except HttpError as e:
            logger.error(f"❌ スプレッドシート更新エラー（行{row_number}）: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 更新エラー（行{row_number}）: {e}")
            return False
    
    def process_all_users(self):
        """全ユーザーのデータを処理"""
        logger.info("🚀 === 処理開始 ===")
        start_time = datetime.now()
        
        # ユーザーIDリストを取得
        users = self.get_user_ids_from_sheet()
        if not users:
            logger.warning("⚠️ 処理対象のユーザーが見つかりません")
            return {
                'status': 'no_users',
                'processed': 0,
                'success': 0,
                'failed': 0
            }
        
        # 処理統計
        stats = {
            'total': len(users),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'results': []
        }
        
        # 各ユーザーを処理
        for user in users:
            user_id = user['user_id']
            row_number = user['row_number']
            
            logger.info(f"📊 処理中 {stats['processed'] + 1}/{stats['total']}: {user_id}")
            
            # スクレイピング実行
            scrape_result = self.scrape_tikleap_profile(user_id)
            
            # スプレッドシート更新
            if scrape_result['success']:
                update_success = self.update_diamond_value(row_number, scrape_result['value'])
                if update_success:
                    stats['success'] += 1
                    status = 'success'
                else:
                    stats['failed'] += 1
                    status = 'update_failed'
            else:
                # エラーの場合もエラーメッセージを記録
                self.update_diamond_value(row_number, f"Error: {scrape_result.get('error', 'Unknown')}")
                stats['failed'] += 1
                status = 'scrape_failed'
            
            stats['processed'] += 1
            stats['results'].append({
                'user_id': user_id,
                'row': row_number,
                'status': status,
                'value': scrape_result.get('value')
            })
        
        # 処理時間
        elapsed_time = (datetime.now() - start_time).total_seconds()
        stats['elapsed_time'] = f"{elapsed_time:.1f}秒"
        
        logger.info(f"✅ === 処理完了 ===")
        logger.info(f"   成功: {stats['success']}/{stats['total']}")
        logger.info(f"   失敗: {stats['failed']}/{stats['total']}")
        logger.info(f"   処理時間: {stats['elapsed_time']}")
        
        return stats

# Flask アプリケーション
app = Flask(__name__)
scraper = None

@app.route('/', methods=['GET'])
def home():
    """ホームページ"""
    return jsonify({
        'service': 'TikLeap Scraper System',
        'status': 'running',
        'spreadsheet_id': '1VuNZSEl2aP0_kmQkxDLxYM3YzC2qXRAZD-dH8XGO-g0',
        'endpoints': {
            '/health': 'ヘルスチェック',
            '/test-connection': 'スプレッドシート接続テスト',
            '/get-users': 'ユーザーID一覧取得',
            '/scrape-test': 'スクレイピングテスト（user_idパラメータ必須）',
            '/process-all': '全ユーザー処理実行'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'initialized': scraper is not None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test-connection', methods=['GET'])
def test_connection():
    """スプレッドシート接続テスト"""
    if not scraper:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        scraper._test_connection()
        return jsonify({
            'status': 'success',
            'message': 'スプレッドシートに正常に接続できました'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get-users', methods=['GET'])
def get_users():
    """ユーザーID一覧を取得"""
    if not scraper:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        users = scraper.get_user_ids_from_sheet()
        return jsonify({
            'status': 'success',
            'count': len(users),
            'users': users
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/scrape-test', methods=['GET'])
def scrape_test():
    """単一ユーザーのスクレイピングテスト"""
    if not scraper:
        return jsonify({'error': 'System not initialized'}), 500
    
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id parameter is required'}), 400
    
    try:
        result = scraper.scrape_tikleap_profile(user_id)
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/process-all', methods=['POST'])
def process_all():
    """全ユーザーの処理を実行"""
    if not scraper:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        stats = scraper.process_all_users()
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    try:
        # システム初期化
        logger.info("🚀 システム起動中...")
        scraper = TikLeapScraper()
        
        # Flask アプリケーション開始
        port = int(os.getenv('PORT', 8080))
        logger.info(f"🌐 Flaskサーバー起動: ポート{port}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ システム起動エラー: {e}")
        # エラーがあってもサーバーは起動する（ヘルスチェックのため）
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
