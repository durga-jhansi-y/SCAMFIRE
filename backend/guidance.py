"""Our own scam taxonomy (T-Mobile supplied none) and plain-language next steps.
Reporting facts: 7726 (SPAM) is the carrier-wide spam text reporting shortcode; reportfraud.ftc.gov is the FTC;
ic3.gov is the FBI's Internet Crime Complaint Center; phishing@irs.gov is the IRS's phishing mailbox."""

REPORT_7726 = "Forward the message to 7726 (SPAM). It's free and helps your carrier block it."
REPORT_FTC = "Report it at reportfraud.ftc.gov."

TAXONOMY = {
    "bank_account_locked": {
        "title": "Fake bank / account alert",
        "what": "Scammers pretend your bank locked your account so you'll hand over a login, PIN or card number.",
        "tactic": "Fear + a link to a copy-cat sign-in page.",
        "steps": ["Don't tap the link or call any number in the message.",
                  "Call your bank using the number on the back of your card.",
                  "If you already entered details, call the bank now and change your password."],
    },
    "package_delivery": {
        "title": "Fake delivery notice",
        "what": "A 'missed delivery' text asking for a small fee, which steals your card details.",
        "tactic": "Small amount, big hurry, look-alike link.",
        "steps": ["Don't pay any 'redelivery fee' through a link.",
                  "Check your real order in the store's app, or type the courier's website yourself.",
                  "Real carriers don't ask for card details by text."],
    },
    "toll_fine": {
        "title": "Fake toll or fine",
        "what": "An unpaid toll or ticket text that sends you to a fake payment page.",
        "tactic": "Small debt + late-fee threat.",
        "steps": ["Don't use the link. Go to your toll authority's real website or app.",
                  "If you really have a balance, it will show up there.",
                  "Report it at ic3.gov if you paid."],
    },
    "irs_government": {
        "title": "Government impersonation",
        "what": "Someone claiming to be the IRS, SSA or police threatens arrest or demands payment.",
        "tactic": "Authority + fear + untraceable payment (gift cards, wire).",
        "steps": ["Hang up or stop replying. Real agencies don't threaten arrest by text or phone.",
                  "No government agency takes gift cards or wires.",
                  "Forward IRS emails to phishing@irs.gov."],
    },
    "tech_support": {
        "title": "Tech support scam",
        "what": "A pop-up, email or call says your device is infected so you'll give remote access or pay.",
        "tactic": "Scary virus claim + a phone number to call.",
        "steps": ["Don't call the number or let anyone control your computer.",
                  "Close the page. Real companies don't send alerts with a phone number.",
                  "If someone has access, turn off Wi-Fi and change your passwords from another device."],
    },
    "romance": {
        "title": "Romance scam",
        "what": "A new 'friend' builds a bond fast, then asks for money, gift cards or crypto.",
        "tactic": "Affection, secrecy, then an emergency that needs money.",
        "steps": ["Never send money, gift cards or crypto to someone you haven't met in person.",
                  "Do a reverse image search on their photos.",
                  "Talk it over with someone you trust. Scammers ask you to keep it secret."],
    },
    "job_offer": {
        "title": "Fake job offer",
        "what": "Easy high-paying work that ends in a bad check or a request for your bank/SSN details.",
        "tactic": "Too-good pay + 'deposit this check and send some back'.",
        "steps": ["Don't share your SSN or bank info before a verified interview.",
                  "Never 'send back' money from a check. The check will bounce.",
                  "Look up the company's real careers page yourself."],
    },
    "prize_lottery": {
        "title": "Fake prize or lottery",
        "what": "You 'won' something, but must pay a fee or enter details to claim it.",
        "tactic": "Excitement + a small fee or a survey link.",
        "steps": ["You can't win a contest you didn't enter. Don't click.",
                  "Never pay a fee to receive a prize.",
                  "Delete the message."],
    },
    "crypto_investment": {
        "title": "Crypto / investment scam",
        "what": "Promises of huge guaranteed returns, often from a stranger who texted 'by mistake'.",
        "tactic": "Friendly opener, fake profits, then you can't withdraw.",
        "steps": ["No real investment guarantees big returns.",
                  "Never share your wallet recovery phrase with anyone.",
                  "Report it at ic3.gov and reportfraud.ftc.gov."],
    },
    "family_emergency": {
        "title": "'Hi Mom, new number' / family emergency",
        "what": "Someone pretends to be your child or grandchild with a new number and urgently needs money.",
        "tactic": "Urgency + secrecy + a payment you can't get back.",
        "steps": ["Call your family member on the number you already have.",
                  "Ask a question only they would know. Some families agree on a code word.",
                  "Don't send money or gift cards until you've talked to them."],
    },
    "carrier_sim_swap": {
        "title": "Carrier / SIM-swap scam",
        "what": "A fake carrier text tries to get your account PIN, which lets a thief take over your number.",
        "tactic": "'Verify your account' + a PIN request.",
        "steps": ["Don't reply with your account PIN or tap the link.",
                  "Check your account in the carrier's app, or dial 611 from your phone.",
                  "Ask your carrier to add a port-out PIN and SIM-protection to your account."],
    },
}
LEGIT_LABELS = {
    "legit_2fa": "Looks like a normal verification code",
    "legit_delivery": "Looks like a normal delivery update",
    "legit_friend": "Looks like a normal personal message",
    "legit_appointment": "Looks like a normal reminder",
    "legit_bank_alert": "Looks like a normal bank notice",
    "legit_carrier": "Looks like a normal carrier notice",
}

LEGIT_WHY = {
    "legit_2fa": "A real code text just gives you the code and tells you not to share it. It doesn't ask you to click, call or reply with anything.",
    "legit_delivery": "Real delivery notices use the courier's own website or app, and never ask for a fee or card details by text.",
    "legit_friend": "This is ordinary chat. It doesn't mix pressure, secrecy and a payment you can't undo. If a request for money surprises you, you can still call to check.",
    "legit_appointment": "Reminders come from someone you already do business with, and the only thing they ask is to confirm or reschedule.",
    "legit_bank_alert": "Real bank alerts say to use your app or the number on your card. They never ask for your PIN, password or a code.",
    "legit_carrier": "Real carrier notices point you to the official app or tell you to dial 611. They don't demand a payment link or your PIN.",
}

# One short habit per category. A missed scam shows its habit in the end-of-round summary.
HABITS = {
    "bank_account_locked": "Never tap a link in a 'your account is locked' message. Call the number on the back of your card.",
    "package_delivery": "Never pay a 'redelivery fee' from a text. Check the order in the store's app or the courier's own site.",
    "toll_fine": "Ignore toll and fine links. Check your balance on the real toll website that you type in yourself.",
    "irs_government": "Real agencies don't threaten arrest or take gift cards. Hang up and look up the agency's real number.",
    "tech_support": "No real company puts a phone number in a virus warning. Never give anyone remote access.",
    "romance": "Never send money, gift cards or crypto to someone you haven't met in person, however close you feel.",
    "job_offer": "A real employer never asks you to deposit a check and send money back, or for your SSN before you're hired.",
    "prize_lottery": "You can't win a contest you didn't enter, and real prizes never cost a fee to claim.",
    "crypto_investment": "Guaranteed big returns are always a lie. Never share your wallet recovery phrase.",
    "family_emergency": "Before sending money to a 'new number' family member, call them on the number you already have.",
    "carrier_sim_swap": "Never reply to a text with your account PIN. Check the carrier app or dial 611 instead.",
}
FALSE_ALARM_HABIT = "Before panicking at a real message, ask: does it ask me to click, pay or share a code? If not, it's probably fine. Check by using the official app."


def next_steps(category: str, verdict: str, confidence: float):
    """Return {risk, headline, steps[]}. Risk: high / medium / low."""
    if verdict == "scam":
        t = TAXONOMY.get(category, {})
        risk = "high" if confidence >= 0.85 else "medium"
        steps = list(t.get("steps", ["Don't click links or reply.", "Contact the company using a number you already trust."]))
        steps += [REPORT_7726, REPORT_FTC, "Then delete it. If you already shared money or details, tell your bank and a family member today."]
        return {"risk": risk, "headline": t.get("title", "Likely a scam"), "steps": steps}
    if verdict == "unsure":
        return {"risk": "medium", "headline": "Not sure. Treat it carefully",
                "steps": ["Don't tap links or call numbers in the message.",
                          "Contact the company or person using a number or app you already trust.",
                          "Never share codes, PINs or passwords, and never pay with gift cards or crypto.",
                          "If you decide it's fake: " + REPORT_7726]}
    return {"risk": "low", "headline": LEGIT_LABELS.get(category, "Looks fine"),
            "steps": ["Nothing in this message looks like a known scam pattern. No detector is perfect.",
                      "Still never share a one-time code with anyone who contacts you.",
                      "If something feels off, check directly with the sender by a number you already have."]}
