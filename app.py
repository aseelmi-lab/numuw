from flask import Flask, request, jsonify, send_from_directory
import anthropic
import os
import json
import re

app = Flask(__name__, static_folder='.')
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "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"))

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

IMPORTANT: يجب أن يكون ردك JSON فقط وفقط. لا تكتب أي نص قبل أو بعد JSON. لا تستخدم ```json أو ``` أبداً. ابدأ ردك مباشرة بـ { وانهِه بـ }

الشكل المطلوب:
{"message":"ردك هنا","has_data":false,"early_warning":null,"stress_level":null,"stress_reason":null,"data":null,"verdict":null,"loan_details":null,"plan_a":null,"plan_b":null,"quick_replies":null,"decision_quality":null,"decision_reasons":null,"rescue_plan":null,"scenarios":null}

عند وجود بيانات مالية كاملة استخدم has_data:true وأكمل حقل data.
quick_replies: أضفها دائماً لو السؤال إجابته بسيطة.
loan_details: أضفها كلما ذكر المستخدم قرضاً مع مبلغ ومدة.
plan_a و plan_b: أضفهما بعد كل تحليل مالي كامل.
لو معلومات ناقصة اسأل سؤالاً واحداً فقط."""

EMPTY = {"message": "", "has_data": False, "early_warning": None, "stress_level": None,
         "stress_reason": None, "data": None, "verdict": None, "loan_details": None,
         "plan_a": None, "plan_b": None, "quick_replies": None, "decision_quality": None,
         "decision_reasons": None, "rescue_plan": None, "scenarios": None}

def parse_response(raw):
    raw = raw.strip()
    # محاولة 1: JSON مباشر
    try:
        return json.loads(raw)
    except:
        pass
    # محاولة 2: استخراج أول كتلة JSON
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    # محاولة 3: إزالة code blocks
    cleaned = re.sub(r'```(?:json)?', '', raw).strip()
    try:
        return json.loads(cleaned)
    except:
        pass
    # fallback
    result = dict(EMPTY)
    result["message"] = raw
    return result

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
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=SYSTEM_PROMPT + profile_context,
            messages=messages
        )
        raw = response.content[0].text.strip()
        parsed = parse_response(raw)
    except Exception as e:
        parsed = dict(EMPTY)
        parsed["message"] = f"حدث خطأ في الاتصال: {str(e)}"
    return jsonify(parsed)

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    data = request.json
    image_data = data.get('image')
    media_type = data.get('media_type', 'image/jpeg')
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": "حلل هذه الوثيقة المالية واستخرج منها جميع الأرقام والمعلومات"}
            ]}]
        )
        raw = response.content[0].text.strip()
        parsed = parse_response(raw)
    except Exception as e:
        parsed = dict(EMPTY)
        parsed["message"] = f"حدث خطأ في تحليل الصورة: {str(e)}"
    return jsonify(parsed)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
