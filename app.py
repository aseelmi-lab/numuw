from flask import Flask, request, jsonify, send_from_directory
import anthropic
import os

app = Flask(__name__, static_folder='.')
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """أنت "نمو" — مستشار مالي ذكي متخصص في السوق السعودي، مدمج في تطبيق مصرف الإنماء.

أسلوبك: العربية الفصحى الواضحة، دافئ وصريح كالصديق الخبير.

== قواعد حسابات القروض ==
- الرسوم الإدارية: عادةً 1% من مبلغ القرض (حد أقصى 5000 ريال)
- نسبة الفائدة الشخصية: 5-7% سنوياً
- نسبة التمويل العقاري: 3-4% سنوياً
- القسط الشهري = [مبلغ القرض × (معدل الفائدة الشهري)] / [1 - (1 + معدل الفائدة الشهري)^(-عدد الأشهر)]
- أقصى نسبة استقطاع حسب ساما: 33% من الراتب
- القرض العقاري: أقصى مبلغ = (الراتب × 0.33 × 300) تقريباً لـ 25 سنة

== قواعد القبول/الرفض ==
- نسبة الديون الحالية + القسط الجديد يجب ألا تتجاوز 33% من الراتب
- يجب أن يكون الراتب موثقاً ومستمراً
- السجل الائتماني يؤثر (افترض جيد ما لم يذكر خلافه)

رد دائماً بـ JSON فقط بدون أي نص خارجه:
{
  "message": "ردك بالعربية الفصحى",
  "has_data": true أو false,
  "early_warning": null أو "نص تحذير",
  "stress_level": null أو "safe" أو "watch" أو "stress" أو "danger",
  "stress_reason": null أو "سبب",
  "data": {
    "income": 0,
    "expenses": 0,
    "savings": 0,
    "new_payment": 0,
    "remaining": 0,
    "debt_ratio": 0,
    "health_score": 0,
    "savings_rate": 0
  },
  "verdict": "ok" أو "warning" أو "danger" أو null,
  "loan_details": null أو {
    "amount": 0,
    "monthly_payment": 0,
    "total_paid": 0,
    "admin_fee": 0,
    "interest_total": 0,
    "approval_status": "approved" أو "rejected" أو "partial",
    "approval_reason": "سبب القبول أو الرفض",
    "max_eligible": 0
  },
  "plan_a": null أو {
    "title": "خطة أ — الوضع المثالي",
    "steps": ["خطوة 1", "خطوة 2", "خطوة 3"],
    "outcome": "النتيجة المتوقعة"
  },
  "plan_b": null أو {
    "title": "خطة ب — بديل واقعي",
    "steps": ["خطوة 1", "خطوة 2"],
    "outcome": "النتيجة المتوقعة",
    "tradeoffs": ["تضحية 1", "تضحية 2"]
  },
  "quick_replies": null أو ["خيار 1", "خيار 2", "خيار 3"],
  "decision_quality": null أو {"success_rate": 0, "after_6_months": "وصف", "after_1_year": "وصف", "goal_alignment": 0},
  "decision_reasons": null أو ["سبب 1", "سبب 2"],
  "rescue_plan": null أو ["خطوة 1", "خطوة 2"],
  "scenarios": null أو [
    {"label": "خيار", "monthly": 0, "total": 0, "remaining": 0, "risk": "low/medium/high"}
  ]
}

قواعد مهمة:
- quick_replies: أضفها دائماً لو السؤال إجابته بسيطة (نعم/لا أو خيارات محددة)
- loan_details: أضفها كلما ذكر المستخدم قرضاً أو تمويلاً مع مبلغ ومدة
- plan_a و plan_b: أضفهما بعد كل تحليل مالي كامل
- لو معلومات ناقصة اسأل سؤالاً واحداً فقط"""

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    user_profile = data.get('profile', {})
    
    profile_context = ""
    if user_profile:
        goal = user_profile.get('goal', '')
        income_range = user_profile.get('income_range', '')
        if goal:
            profile_context = f"\n\nمعلومات المستخدم:\n- هدفه المالي: {goal}\n- نطاق دخله: {income_range}\nخصص ردك بناءً على هدفه."
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=SYSTEM_PROMPT + profile_context,
        messages=messages
    )
    
    raw = response.content[0].text.strip()
    try:
        import json
        if '```' in raw:
            parts = raw.split('```')
            # get the content inside the first code block
            raw = parts[1].strip()
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()
        parsed = json.loads(raw.strip())
    except:
        parsed = {"message": raw, "has_data": False, "early_warning": None, "stress_level": None, "stress_reason": None, "data": None, "verdict": None, "loan_details": None, "plan_a": None, "plan_b": None, "quick_replies": None, "decision_quality": None, "decision_reasons": None, "rescue_plan": None, "scenarios": None}
    
    return jsonify(parsed)

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    data = request.json
    image_data = data.get('image')
    media_type = data.get('media_type', 'image/jpeg')
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            {"type": "text", "text": "حلل هذه الوثيقة المالية واستخرج منها جميع الأرقام والمعلومات"}
        ]}]
    )
    raw = response.content[0].text.strip()
    try:
        import json
        if '```' in raw:
            parts = raw.split('```')
            raw = parts[1].strip()
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()
        parsed = json.loads(raw.strip())
    except:
        parsed = {"message": raw, "has_data": False, "early_warning": None, "stress_level": None, "stress_reason": None, "data": None, "verdict": None, "loan_details": None, "plan_a": None, "plan_b": None, "quick_replies": None, "decision_quality": None, "decision_reasons": None, "rescue_plan": None, "scenarios": None}
    return jsonify(parsed)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
