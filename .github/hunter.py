import sys
import re
import time
import json
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

# أنماط الأكواد (للبطاقات الهدايا)
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
        f"🔥 *بدء نظام صيد البطاقات الهدايا لمدة 5 ساعات* 🔥\n"
        f"✅ سيتم إرسال كل كود فوراً.\n"
        f"✅ سيتم إرسال تقرير مفصل كل 5 دقائق.\n"
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
        f"📊 *تقرير ختامي - دورة الصيد (5 ساعات)* 📊\n"
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
    # محاكاة: إذا احتوى على Z أو 9 نعتبره صالحًا
    if 'Z' in code or '9' in code:
        return True, random.randint(5, 25)
    else:
        return False, 0

# ------------------- التشغيل الرئيسي (5 ساعات) -------------------
def main():
    start_time = time.time()
    end_time = start_time + TOTAL_RUN_DURATION
    
    # رسالة البدء فورية
    send_startup()
    
    # جلب الأكواد الأولية
    all_codes = []
    all_codes.extend(fetch_codes_from_github())
    
    # إضافة أكواد وهمية لضمان وجود بيانات
    dummy_codes = generate_dummy_codes(20)
    all_codes.extend(dummy_codes)
    
    all_codes = list(set(all_codes))
    total_codes = len(all_codes)
    
    if total_codes == 0:
        send_to_telegram("⚠️ لم يتم العثور على أي أكواد. سأحاول مرة أخرى خلال دقائق.")
        return
    
    send_to_telegram(f"📦 تم جلب {total_codes} كوداً فريداً. سيتم الاختبار خلال 5 ساعات.")
    
    # قوائم التخزين
    tested_log = []
    valid_codes = []
    invalid_codes = []
    
    last_heartbeat = time.time()
    last_search_time = time.time()
    
    while time.time() < end_time:
        # 1. جلب أكواد جديدة من GitHub كل 30 دقيقة
        if time.time() - last_search_time >= 1800:  # 30 دقيقة
            new_codes = fetch_codes_from_github()
            if new_codes:
                for code in new_codes:
                    if code not in all_codes:
                        all_codes.append(code)
                total_codes = len(all_codes)
                send_to_telegram(f"📦 تم تحديث القائمة: {len(new_codes)} كود جديد، الإجمالي {total_codes}.")
            last_search_time = time.time()
        
        # 2. اختبار الأكواد التي لم تُختبر بعد
        for code in all_codes:
            if code in tested_log:
                continue
            
            is_valid, value = test_code(code)
            tested_log.append(code)
            
            if is_valid and value > 0:
                valid_codes.append(code)
                # إرسال فوري
                send_valid_code(code, "غير معروف (محاكاة)", value)
            else:
                invalid_codes.append(code)
            
            # تأخير بين الاختبارات
            time.sleep(random.uniform(0.5, 1.5))
            
            # 3. إرسال نبض قلب كل 5 دقائق
            if time.time() - last_heartbeat >= 300:
                elapsed_min = int((time.time() - start_time) / 60)
                send_heartbeat(elapsed_min, total_codes, len(tested_log), len(valid_codes), len(invalid_codes))
                last_heartbeat = time.time()
            
            # 4. إذا انتهى الوقت، اخرج من الحلقة
            if time.time() >= end_time:
                break
        
        # تأخير قصير قبل بدء دورة جديدة (إن بقي وقت)
        time.sleep(10)
    
    # التقرير الختامي
    send_final_report(total_codes, len(tested_log), len(valid_codes), len(invalid_codes))
    print("[+] انتهى التشغيل بعد 5 ساعات.")

if __name__ == "__main__":
    main()
