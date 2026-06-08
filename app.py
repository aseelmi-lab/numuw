from flask import Flask, request, jsonify, send_from_directory
import anthropic
import os

app = Flask(__name__, static_folder='.')
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """أنت "نمو" — مستشار مالي ذكي ومتخصص في السوق السعودي، مدمج في تطبيق مصرف الإنماء.

أسلوبك: العربية الفصحى الواضحة، دافئ وصريح، كالصديق الخبير.

تحلل: الراتب، المصروفات، المدخرات، الديون، الأهداف المالية.

قواعد ساما: نسبة الديون لا تتجاوز 33% من الدخل.

معدلات السعوديين:
- الإيجار: 25-30% | المطاعم: 10-12% | التسوق: 8-10% | الادخار المثالي: 20%

رد دائماً بـ JSON فقط بدون أي نص خارجه:
{
  "message": "ردك بالعربية الفصحى",
  "has_data": true أو false,
  "early_warning": null أو "نص تحذير",
  "stress_level": null أو "safe" أو "watch" أو "stress" أو "danger",
  "stress_reason": null أو "سبب مستوى الضغط",
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
  "decision_quality": null أو {"success_rate": 0, "after_6_months": "وصف", "after_1_year": "وصف", "goal_alignment": 0},
  "decision_reasons": null أو ["سبب 1", "سبب 2", "سبب 3"],
  "rescue_plan": null أو ["خطوة 1", "خطوة 2"],
  "scenarios": null أو [
    {"label": "الخيار الأول", "monthly": 0, "total": 0, "remaining": 0, "risk": "low/medium/high"},
    {"label": "الخيار الثاني", "monthly": 0, "total": 0, "remaining": 0, "risk": "low/medium/high"},
    {"label": "تأجيل 6 أشهر", "monthly": 0, "total": 0, "remaining": 0, "risk": "low/medium/high"}
  ],
  "saudi_comparison": null أو [
    {"category": "الفئة", "user_pct": 0, "avg_pct": 0, "status": "good/bad"}
  ]
}

قواعد مهمة:
- stress_level: دائماً احسبه لو عندك بيانات كافية
- decision_quality: فقط لو المستخدم يسأل عن قرار محدد
- decision_reasons: دائماً اشرح السبب لو عندك verdict
- scenarios: 3 خيارات دائماً لو سأل عن قرض أو شراء
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
            profile_context = f"\n\nمعلومات المستخدم:\n- هدفه المالي: {goal}\n- نطاق دخله: {income_range}\n\nمهم: خصص ردك وتحليلك بناءً على هدفه. مثلاً لو هدفه شراء منزل اذكر مدى قربه أو بعده عن الهدف. لو هدفه سيارة قدم مقارنة خيارات التمويل."
    
    system = SYSTEM_PROMPT + profile_context
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=system,
        messages=messages
    )
    
    raw = response.content[0].text.strip()
    
    try:
        import json
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except:
        parsed = {
            "message": raw,
            "has_data": False,
            "early_warning": None,
            "stress_level": None,
            "stress_reason": None,
            "data": None,
            "verdict": None,
            "decision_quality": None,
            "decision_reasons": None,
            "rescue_plan": None,
            "scenarios": None,
            "saudi_comparison": None
        }
    
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
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": "حلل هذه الوثيقة المالية واستخرج منها جميع الأرقام والمعلومات المالية وقدم تحليلاً شاملاً"}
            ]
        }]
    )
    
    raw = response.content[0].text.strip()
    try:
        import json
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except:
        parsed = {"message": raw, "has_data": False, "early_warning": None, "stress_level": None, "stress_reason": None, "data": None, "verdict": None, "decision_quality": None, "decision_reasons": None, "rescue_plan": None, "scenarios": None, "saudi_comparison": None}
    
    return jsonify(parsed)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
