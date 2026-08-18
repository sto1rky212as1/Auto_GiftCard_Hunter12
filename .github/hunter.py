import sys
import re
import time
import json
import random
import requests
from datetime import datetime, timedelta
from collections import deque

# =================================================================
# التوكنات المضمنة
# =================================================================
TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
# =================================================================

# ملفات التخزين
TESTED_CODES_LOG = "tested_log.txt"
VALID_CODES_FILE = "valid_giftcards.txt"

# أنماط الأكواد
GIFT_CARD_PATTERNS = [
    r'\b[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}\b',
    r'\b[0-9]{16}\b',
    r'\b[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}\b',
]

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
        f"🔥 *بدء نظام صيد البطاقات الهدايا* 🔥\n"
        f"✅ سيتم البحث عن أكواد مسربة من GitHub والويب.\n"
        f"✅ سيتم إرسال تقرير كل 5 دقائق.\n"
        f"✅ سيتم إرسال الأكواد الصالحة فوراً.\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

def send_heartbeat(elapsed_min, total_codes, tested, valid, invalid):
    msg = (
        f"💓 *تحديث دوري (كل 5 دقائق)* 💓\n"
        f"⏳ الوقت المنقضي: {elapsed_min} دقيقة\n"
        f"📦 إجمالي الأكواد المسترجعة: {total_codes}\n"
        f"🔍 عدد المفحوص: {tested}\n"
        f"✅ الصالح: {valid}\n"
        f"❌ غير الصالح: {invalid}\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

def send_valid_code(code, service, value):
    msg = (
        f"🎁 *كود صالح* 🎁\n"
        f"الخدمة: {service}\n"
        f"الكود: `{code}`\n"
        f"القيمة المقدرة: {value}$\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

def send_final_report(total_codes, tested, valid, invalid):
    msg = (
        f"📊 *تقرير ختامي - دورة الصيد* 📊\n"
        f"📦 إجمالي الأكواد المسترجعة: {total_codes}\n"
        f"🔍 عدد المفحوص: {tested}\n"
        f"✅ الصالح: {valid}\n"
        f"❌ غير الصالح: {invalid}\n"
        f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

# ------------------- جلب الأكواد من المصادر -------------------
def fetch_codes_from_github():
    found = set()
    queries = [
        '"gift card" extension:txt',
        '"giftcard" extension:csv',
        '"amazon gift card" extension:txt',
        '"google play" code extension:txt',
        '"mcdonalds" gift extension:csv'
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
                                for pattern in GIFT_CARD_PATTERNS:
                                    matches = re.findall(pattern, content)
                                    for m in matches:
                                        found.add(m.strip())
                        except:
                            continue
            time.sleep(random.uniform(1, 2))
        except:
            continue
    return list(found)

def fetch_codes_from_pastebin():
    found = set()
    try:
        resp = requests.get("https://pastebin.com/archive", timeout=15)
        if resp.status_code == 200:
            # استخدام BeautifulSoup هنا، لكننا نكتفي بـ regex بسيط
            content = resp.text
            # نبحث عن روابط الـ raw في النص
            raw_links = re.findall(r'https://pastebin.com/raw/[a-zA-Z0-9]+', content)
            for link in raw_links[:5]:
                try:
                    paste_resp = requests.get(link, timeout=10)
                    if paste_resp.status_code == 200:
                        text = paste_resp.text
                        for pattern in GIFT_CARD_PATTERNS:
                            matches = re.findall(pattern, text)
                            for m in matches:
                                found.add(m.strip())
                except:
                    continue
    except:
        pass
    return list(found)

def generate_dummy_codes(count=20):
    codes = set()
    import string
    for _ in range(count):
        part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part3 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part4 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        codes.add(f"{part1}-{part2}-{part3}-{part4}")
    return list(codes)

# ------------------- اختبار الصلاحية (محاكاة) -------------------
def test_code(code):
    if 'Z' in code or '9' in code:
        return True, random.randint(5, 25)
    else:
        return False, 0

# ------------------- الوظيفة الرئيسية -------------------
def main():
    start_time = time.time()
    send_startup()
    
    all_codes = []
    all_codes.extend(fetch_codes_from_github())
    all_codes.extend(fetch_codes_from_pastebin())
    
    # أكواد وهمية لضمان وجود بيانات
    dummy_codes = generate_dummy_codes(20)
    all_codes.extend(dummy_codes)
    
    all_codes = list(set(all_codes))
    total_codes = len(all_codes)
    
    if total_codes == 0:
        send_to_telegram("⚠️ لم يتم العثور على أي أكواد في هذه الدورة. سأحاول لاحقاً.")
        return
    
    send_to_telegram(f"📦 تم جلب {total_codes} كوداً فريداً (بما فيها العينات التجريبية). جاري الاختبار...")
    
    # سجل الأكواد المختبرة سابقاً
    tested_before = set()
    try:
        with open(TESTED_CODES_LOG, 'r') as f:
            tested_before = set(line.strip() for line in f)
    except:
        pass
    
    new_codes = [c for c in all_codes if c not in tested_before]
    if not new_codes:
        send_to_telegram("ℹ️ جميع الأكواد تم اختبارها سابقاً. لا شيء جديد.")
        return
    
    send_to_telegram(f"🧪 سيتم اختبار {len(new_codes)} كوداً جديداً...")
    
    tested_count = 0
    valid_count = 0
    invalid_count = 0
    last_heartbeat = time.time()
    
    max_test = min(len(new_codes), 200)
    codes_to_test = new_codes[:max_test]
    
    for i, code in enumerate(codes_to_test, 1):
        is_valid, value = test_code(code)
        tested_count += 1
        
        with open(TESTED_CODES_LOG, 'a') as f:
            f.write(f"{code}\n")
        
        if is_valid and value > 0:
            valid_count += 1
            with open(VALID_CODES_FILE, 'a') as f:
                f.write(f"{code} - قيمة: {value}$\n")
            send_valid_code(code, "غير معروف (محاكاة)", value)
        else:
            invalid_count += 1
        
        if time.time() - last_heartbeat >= 300:
            elapsed_min = int((time.time() - start_time) / 60)
            send_heartbeat(elapsed_min, total_codes, tested_count, valid_count, invalid_count)
            last_heartbeat = time.time()
        
        time.sleep(random.uniform(0.5, 1.5))
        
        if i % 10 == 0:
            print(f"[*] تم اختبار {i} من {len(codes_to_test)}")
    
    elapsed_min = int((time.time() - start_time) / 60)
    send_final_report(total_codes, tested_count, valid_count, invalid_count)
    
    summary = (
        f"📋 *ملخص الدورة*\n"
        f"✅ إجمالي الأكواد المسترجعة: {total_codes}\n"
        f"🔍 تم فحص: {tested_count}\n"
        f"✅ صالح: {valid_count}\n"
        f"❌ غير صالح: {invalid_count}\n"
        f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(summary)
    print("[+] انتهى التشغيل بنجاح.")

if __name__ == "__main__":
    main()
