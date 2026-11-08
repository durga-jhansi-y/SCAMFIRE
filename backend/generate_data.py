"""Synthetic labeled message generator for Scam Fire Drill.

Output: data/synthetic/messages.csv
Columns: id, text, channel, label, category, red_flags

Templates mark red-flag spans inline as [[flag_type|span text]]. The span text stays in the
message; flag_type + span are recorded in `red_flags` (as "type:span" joined by " || ") so the
UI can highlight them. Everything here is FAKE: names, numbers, and domains are invented
(555-01xx numbers, .example / obviously-fake domains).

Usage: python backend/generate_data.py [--n 500] [--seed 7]
"""
import argparse
import csv
import random
import re
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "messages.csv"

# ---------- slot values ----------
NAMES = ["Sam", "Maria", "Jake", "Priya", "Tom", "Linda", "Carlos", "Aisha", "Dave", "Emily"]
BANKS = ["Chase", "Wells Fargo", "Bank of America", "Citi", "US Bank", "Capital One"]
CARRIERS = ["T-Mobile", "T-Mobile", "your carrier"]
COURIERS = ["USPS", "UPS", "FedEx", "DHL"]
BAD_DOMAINS = ["bit.ly/3xK9aQ", "tinyurl.com/y8fz2p", "secure-verify-login.top", "usps-redelivery.info",
               "acct-update-now.xyz", "t-mobile-billing.support", "chase-secure-alert.co", "irs-refund-claim.net",
               "fastpay-verify.click", "cutt.ly/Rq7vPz", "track-parcel-now.cc"]
GOOD_DOMAINS = ["t-mobile.com/myaccount", "usps.com/tracking", "ups.com/track", "chase.com", "fedex.com/track"]
AMOUNTS = ["$149.99", "$1,284.50", "$89.00", "$2,500", "$412.37", "$699.00", "$35.50"]
CITIES = ["Dallas", "Austin", "Richardson", "Plano", "Houston"]
SHORT_CODE = ["48213", "902741", "73415", "560218", "119034", "384920"]
FAKE_PHONES = ["(972) 555-0142", "(214) 555-0188", "(469) 555-0171", "(800) 555-0199", "(512) 555-0123"]
CRYPTOS = ["Bitcoin", "USDT", "Ethereum"]
GIFT = ["Apple", "Google Play", "Target", "Steam"]
DOCTORS = ["Dr. Patel", "Dr. Nguyen", "Dr. Brooks", "Dr. Alvarez"]


def slots():
    return {
        "name": random.choice(NAMES), "name2": random.choice(NAMES), "bank": random.choice(BANKS),
        "carrier": random.choice(CARRIERS), "courier": random.choice(COURIERS),
        "bad": random.choice(BAD_DOMAINS), "good": random.choice(GOOD_DOMAINS),
        "amt": random.choice(AMOUNTS), "city": random.choice(CITIES), "code": random.randint(100000, 999999),
        "phone": random.choice(FAKE_PHONES), "crypto": random.choice(CRYPTOS), "gift": random.choice(GIFT),
        "doc": random.choice(DOCTORS), "hrs": random.choice([2, 12, 24, 48]), "pct": random.choice([180, 250, 400, 600]),
        "pay": random.choice([22, 35, 48]), "sc": random.choice(SHORT_CODE), "trk": random.randint(10**9, 10**10 - 1),
        "day": random.choice(["Tuesday", "Thursday", "Monday", "Friday"]), "time": random.choice(["9:30 AM", "2:15 PM", "4:00 PM", "11:45 AM"]),
    }


# ---------- SCAM templates: (channel, text) ----------
SCAM = {
    "bank_account_locked": [
        ("sms", "[[impersonation|{bank} Alert]]: Your account has been [[threat|temporarily locked]] due to suspicious activity. [[urgency|Verify within {hrs} hours]] or it will be closed: [[link|{bad}]]"),
        ("sms", "{bank}: Unusual sign-in from {city}. If this wasn't you, [[credential_request|confirm your login and PIN]] here: [[link|{bad}]]"),
        ("email", "Subject: [[urgency|Action Required]] - Account Suspended\n\nDear Customer,\n\nWe detected a [[threat|suspicious transaction of {amt}]] on your {bank} account. To avoid permanent suspension, [[credential_request|verify your identity and card number]] at [[link|{bad}]].\n\n{bank} Security Team"),
        ("voicemail", "This is an automated message from the {bank} fraud department. Your debit card has been [[threat|compromised]]. [[urgency|Press 1 immediately]] to speak with an agent and [[credential_request|have your card number and PIN ready]]."),
        ("sms", "Your {bank} card ending in 4821 was declined. [[urgency|Reactivate now]] to avoid fees: [[link|{bad}]]"),
    ],
    "package_delivery": [
        ("sms", "[[impersonation|{courier}]]: Your package {trk} could not be delivered. [[payment|Pay a $1.99 redelivery fee]] at [[link|{bad}]] [[urgency|within 24h]] or it will be returned."),
        ("sms", "{courier} Notice: [[urgency|Final attempt]]. Address incomplete for parcel. [[credential_request|Confirm your address and card details]]: [[link|{bad}]]"),
        ("email", "Subject: Delivery failed - [[urgency|action needed]]\n\nWe tried to deliver your parcel but [[credential_request|a customs fee is required]]. [[payment|Pay {amt}]] via [[link|{bad}]] to release your package.\n\n{courier} Customer Care"),
        ("voicemail", "Hello, this is {courier}. We have a package held for you. [[payment|A small fee is required]] to release it. [[urgency|Call back right away]] at {phone} or it will be destroyed."),
    ],
    "toll_fine": [
        ("sms", "NTTA: You have an [[threat|unpaid toll balance of {amt}]]. [[threat|Late fees will apply]] after today. [[payment|Pay now]]: [[link|{bad}]]"),
        ("sms", "[[impersonation|Texas Toll Services]]: Final notice - [[threat|unpaid toll]] of $11.40. [[urgency|Pay within 12 hours]] to avoid a [[threat|$50 penalty and license hold]]: [[link|{bad}]]"),
        ("email", "Subject: [[threat|Traffic violation notice]]\n\nA camera recorded a violation under your plate. [[payment|Pay the {amt} fine online]] at [[link|{bad}]] [[urgency|today]] to avoid court action."),
    ],
    "irs_government": [
        ("sms", "[[impersonation|IRS]]: You are owed a tax refund of {amt}. [[credential_request|Submit your SSN and bank details]] to claim: [[link|{bad}]]"),
        ("voicemail", "This is the [[impersonation|Internal Revenue Service]]. A [[threat|warrant has been issued for your arrest]] over unpaid taxes. [[urgency|Call back immediately]] at {phone}. [[payment|Payment by gift card or wire is accepted]]."),
        ("voicemail", "This is [[impersonation|Social Security Administration]]. Your number has been [[threat|suspended due to criminal activity]]. [[urgency|Press 1 now]] or [[threat|legal action will begin]]."),
        ("email", "Subject: [[impersonation|Department of Treasury]] - Final Notice\n\nYou owe {amt} in back taxes. [[threat|Failure to respond in {hrs} hours will result in seizure of assets]]. [[payment|Pay by {gift} gift card]] and send the code."),
    ],
    "tech_support": [
        ("email", "Subject: [[threat|Your computer is infected]]\n\n[[impersonation|Microsoft Security]] detected [[threat|a virus on your device]]. [[urgency|Call immediately]]: {phone}. Do not turn off your computer."),
        ("voicemail", "This is [[impersonation|Apple Support]]. Your iCloud was [[threat|hacked]]. [[urgency|Call us now]] at {phone}. We will need [[credential_request|remote access to your computer]]."),
        ("sms", "[[impersonation|Norton]]: Your subscription renewed for {amt}. If you didn't authorize this, [[urgency|call {phone} now]] for a refund."),
        ("sms", "[[threat|Your Windows license has expired]]. [[urgency|Renew now]] at [[link|{bad}]] to avoid data loss."),
    ],
    "romance": [
        ("sms", "Hi {name}, I'm sorry to text out of the blue. I think we matched online... I feel a real connection. Can we move to [[link|WhatsApp]]? I'm a [[impersonation|military engineer overseas]] and rarely get signal."),
        ("sms", "My love, I'm stuck at the airport and my card is blocked. Could you [[payment|send {amt} in {gift} gift cards]]? I'll [[urgency|pay you back the moment I land]]. Please don't tell anyone, they won't understand us."),
        ("email", "Subject: Missing you\n\nDarling, I need [[payment|{amt} for a plane ticket]] to finally come see you. [[payment|Wire it via {crypto}]] and keep this [[urgency|just between us]]."),
    ],
    "job_offer": [
        ("sms", "Hi {name}! We found your resume. [[payment|Earn ${pay}/hr working from home]], no experience needed. [[urgency|Limited spots]]. Text back to start: [[link|{bad}]]"),
        ("email", "Subject: Job offer - [[urgency|accept today]]\n\nCongratulations! You've been hired as a remote assistant. We'll send a check for {amt}; [[payment|deposit it and wire back the extra for equipment]]. [[credential_request|Send your SSN and bank info]] to set up payroll."),
        ("sms", "Part-time data entry job, [[payment|${pay}/hr, paid daily]]. [[credential_request|Message us your full name and bank info]] on Telegram to be onboarded. [[urgency|Today only]]."),
    ],
    "prize_lottery": [
        ("sms", "[[impersonation|{carrier}]] Rewards: Congrats! You've [[prize|won a $1,000 gift card]]! [[urgency|Claim in {hrs}h]]: [[link|{bad}]]"),
        ("email", "Subject: [[prize|You are our lucky winner!]]\n\nYour number was selected in the International Lottery ({amt}). To release funds, [[payment|pay a processing fee]] and [[credential_request|send your ID and bank account]]."),
        ("sms", "You've been chosen for a [[prize|free iPhone 16]]! [[urgency|Only 3 left]]. Take our survey: [[link|{bad}]]"),
    ],
    "crypto_investment": [
        ("sms", "Hi, wrong number? Anyway, my uncle's trading team made me [[prize|{pct}% returns in a month]] with {crypto}. I can [[urgency|show you how, spots are filling fast]]: [[link|{bad}]]"),
        ("email", "Subject: [[prize|Guaranteed {pct}% returns]]\n\nJoin our exclusive {crypto} platform. [[payment|Deposit just {amt}]] today and [[prize|double it in 7 days, risk free]]. [[urgency|Offer ends tonight]]."),
        ("sms", "Your {crypto} wallet has a [[threat|security issue]]. [[credential_request|Enter your recovery phrase]] to secure it: [[link|{bad}]]"),
    ],
    "family_emergency": [
        ("sms", "Hi Mom, [[impersonation|this is my new number]]. My phone broke. Can you [[payment|send {amt} for a bill I need to pay today]]? [[urgency|It's urgent]], I'll explain later."),
        ("sms", "Grandma it's me, I'm in [[threat|trouble, I got arrested]] and need [[payment|bail money]]. [[urgency|Please don't tell Mom and Dad]]. Can you [[payment|buy {gift} gift cards]]?"),
        ("voicemail", "Hi, it's me... I [[threat|had an accident]] and I'm [[threat|in the hospital]]. My phone is dead, I'm using someone else's. I [[payment|need money wired right now]]. [[urgency|Please don't call anyone yet]]."),
        ("sms", "Dad, new number, lost my phone. [[payment|Can you Zelle {amt}]] to a friend of mine? [[urgency|Need it in an hour]]."),
    ],
    "carrier_sim_swap": [
        ("sms", "[[impersonation|{carrier}]]: A SIM change was requested on your line. If this wasn't you, [[credential_request|reply with your account PIN]] or visit [[link|{bad}]] [[urgency|immediately]]."),
        ("sms", "{carrier} Alert: Your bill of {amt} is [[threat|overdue and service will be suspended]]. [[payment|Pay now]] at [[link|{bad}]]."),
        ("voicemail", "This is {carrier} security. We noticed [[threat|someone trying to port your number]]. [[credential_request|Please say your account PIN and last four of your SSN]] to cancel the request."),
        ("email", "Subject: [[urgency|Verify your {carrier} account]]\n\nYou qualify for a [[prize|free phone upgrade]]. [[credential_request|Log in with your PIN and password]] at [[link|{bad}]] within {hrs} hours."),
    ],
}

# ---------- LEGIT templates (incl. near-misses that look scammy) ----------
LEGIT = {
    "legit_2fa": [
        ("sms", "Your {carrier} verification code is {code}. It expires in 10 minutes. Never share this code with anyone."),
        ("sms", "{bank}: Your one-time passcode is {code}. We will never call or text asking for it."),
        ("sms", "G-{code} is your Google verification code."),
        ("sms", "Your login code is {code}. If you didn't request this, you can ignore this message."),
    ],
    "legit_delivery": [
        ("sms", "{courier}: Your package {trk} is out for delivery today. Track at {good}."),
        ("email", "Subject: Your order has shipped\n\nHi {name}, your order shipped and should arrive {day}. Track it anytime at {good}. No action needed."),
        ("sms", "{courier}: Delivered. Your package was left at the front door at {time}."),
        ("sms", "{courier} Delivery Alert: a package requires a signature. Reply with a time window or reschedule at {good}."),
    ],
    "legit_friend": [
        ("sms", "hey it's {name}! running 10 min late, grab us a table?"),
        ("sms", "Did you see the game last night?? unreal. Dinner {day}?"),
        ("sms", "Mom here, this is my new work number so save it. Call me when you get a chance, no rush."),
        ("sms", "Hi, it's {name} from book club. Can you send me {amt}? Just your share of the tickets, Venmo is fine, I'll see you {day} too."),
        ("sms", "Urgent!! forgot my keys, can you let me in? I'm outside"),
    ],
    "legit_appointment": [
        ("sms", "Reminder: you have an appointment with {doc} on {day} at {time}. Reply C to confirm or call the office to reschedule."),
        ("email", "Subject: Appointment confirmation\n\nHi {name}, this confirms your visit on {day} at {time}. Please arrive 10 minutes early and bring your insurance card."),
        ("voicemail", "Hi, this is {doc}'s office calling to confirm your appointment {day} at {time}. Please call us back at {phone} if you need to change it. Thank you."),
    ],
    "legit_bank_alert": [
        ("sms", "{bank}: A purchase of {amt} was made on your card ending 4821. Reply YES if this was you or NO if not. We will never ask for your PIN."),
        ("sms", "{bank} Alert: Your balance is below $50. Log in using the {bank} app to review. Do not reply with personal info."),
        ("email", "Subject: Your statement is ready\n\nYour monthly statement is available in the {bank} app. For your security we never include links asking you to sign in."),
        ("sms", "{bank}: Fraud alert - we blocked a suspicious charge of {amt}. If this was you, call the number on the back of your card."),
    ],
    "legit_carrier": [
        ("sms", "{carrier}: Your bill of {amt} is ready and will autopay on the 15th. View it in the T-Life app."),
        ("sms", "{carrier}: You've used 80% of your high-speed data. Manage your plan in the T-Life app."),
        ("email", "Subject: Your plan is changing\n\nHi {name}, effective next month your plan price changes. Details at {good}. Questions? Dial 611 from your phone."),
    ],
}

SPAN = re.compile(r"\[\[(\w+)\|(.+?)\]\]")


PREFIX = ["", "", "", "", "Hi {name}, ", "Hello, ", "Notice: ", "FYI: "]
SUFFIX = ["", "", "", "", " Reply STOP to opt out.", " Thank you.", " Msg&data rates may apply.", " Have a great day!"]


def render(tpl, channel="sms"):
    # same noise for scam and legit so it can't leak the label
    if channel == "sms":
        tpl = random.choice(PREFIX) + tpl + random.choice(SUFFIX)
    text = tpl.format(**slots())
    flags = [f"{m.group(1)}:{m.group(2)}" for m in SPAN.finditer(text)]
    clean = SPAN.sub(lambda m: m.group(2), text)
    return clean, flags


def build(n, seed):
    random.seed(seed)
    n_scam = round(n * 0.6)
    n_legit = n - n_scam
    rows, seen = [], set()

    def fill(pool, count, label):
        cats = list(pool)
        made = Counter()
        attempts = 0
        while sum(made.values()) < count and attempts < count * 60:
            attempts += 1
            cat = cats[sum(made.values()) % len(cats)]
            channel, tpl = random.choice(pool[cat])
            text, flags = render(tpl, channel)
            if text in seen:
                continue
            seen.add(text)
            made[cat] += 1
            rows.append({"text": text, "channel": channel, "label": label, "category": cat,
                         "red_flags": " || ".join(flags)})

    fill(SCAM, n_scam, "scam")
    fill(LEGIT, n_legit, "legit")
    random.shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["id"] = f"syn-{i:04d}"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rows = build(a.n, a.seed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "channel", "label", "category", "red_flags"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")
    print("label:", dict(Counter(r["label"] for r in rows)))
    print("channel:", dict(Counter(r["channel"] for r in rows)))
    for k, v in sorted(Counter(r["category"] for r in rows).items()):
        print(f"  {k:24s}{v}")


if __name__ == "__main__":
    main()
