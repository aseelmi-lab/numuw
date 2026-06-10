from flask import Flask, request, jsonify, send_from_directory
import anthropic
import os
import json
import re

# قراءة ملف env للمفتاح (للتشغيل المحلي فقط)
# على Render وغيره، المفتاح يجي من متغيرات البيئة مباشرة
try:
    from dotenv import load_dotenv
    for env_file in ['.env', 'env']:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            break
except Exception:
    pass

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

app = Flask(__name__, static_folder='.')
client = anthropic.Anthropic(api_key=API_KEY)

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

IMPORTANT: ردك يجب أن يكون JSON صالح فقط. ابدأ مباشرة بحرف { وانتهِ بحرف }. لا تكتب أي نص قبل أو بعد JSON. لا تستخدم backticks أو علامة ```json نهائياً. تأكد أن جميع النصوص داخل علامات تنصيص مزدوجة وأن JSON صالح للقراءة.

الشكل المطلوب بالضبط:
{"message":"ردك هنا","has_data":false,"early_warning":null,"stress_level":null,"stress_reason":null,"data":null,"verdict":null,"loan_details":null,"plan_a":null,"plan_b":null,"quick_replies":null,"decision_quality":null,"decision_reasons":null,"rescue_plan":null,"scenarios":null}

شرح الحقول:
- message: رسالتك النصية للمستخدم (مطلوب دائماً)
- has_data: true عند وجود تحليل مالي كامل، وحينها املأ data بـ {income, expenses, savings, new_payment, remaining, debt_ratio, health_score, savings_rate}
- early_warning: نص تحذير مبكر أو null
- stress_level: "safe" أو "watch" أو "stress" أو "danger" أو null
- stress_reason: سبب مستوى الضغط أو null
- verdict: "ok" أو "warning" أو "danger" أو null
- loan_details: عند ذكر قرض، املأ {amount, monthly_payment, total_paid, admin_fee, interest_total, approval_status, approval_reason, max_eligible}
- plan_a: عند أي تحليل أو خطة، املأها كاملة بهذا الشكل {"title":"خطة أ — العنوان","steps":["خطوة 1 مفصلة","خطوة 2 مفصلة","خطوة 3 مفصلة"],"outcome":"النتيجة المتوقعة"}. يجب أن تحتوي steps على 3 خطوات على الأقل، ولا تتركها فارغة أبداً.
- plan_b: بديل واقعي كامل {"title":"خطة ب — العنوان","steps":["خطوة 1","خطوة 2"],"outcome":"النتيجة","tradeoffs":["تضحية 1","تضحية 2"]}. يجب ملء steps دائماً.
- decision_quality: عند تقييم أي قرار، املأها كاملة {"success_rate":رقم من 0 إلى 100,"after_6_months":"وصف الوضع بعد 6 أشهر","after_1_year":"وصف الوضع بعد سنة","goal_alignment":رقم من 0 إلى 100}. لا تترك success_rate صفراً إلا لو القرار فاشل فعلاً.
- decision_reasons: قائمة أسباب التقييم
- quick_replies: قائمة خيارات سريعة لو السؤال إجابته بسيطة
- savings_rate: رقم فقط بدون علامة % (مثال: 24 وليس "24%")
- لو معلومات ناقصة اسأل سؤالاً واحداً فقط
- مهم جداً: عندما تذكر plan_a أو plan_b في ردك، يجب أن تملأ حقول steps بخطوات فعلية مفصلة، وليس قوائم فارغة"""

EMPTY = {
    "message": "", "has_data": False, "early_warning": None,
    "stress_level": None, "stress_reason": None, "data": None,
    "verdict": None, "loan_details": None, "plan_a": None,
    "plan_b": None, "quick_replies": None, "decision_quality": None,
    "decision_reasons": None, "rescue_plan": None, "scenarios": None
}

def parse_response(raw):
    """يحاول استخراج JSON صالح من رد الموديل بعدة طرق."""
    raw = (raw or "").strip()

    # إزالة code blocks بكل أشكالها أول شي (```json ... ``` أو ``` ... ```)
    cleaned = raw
    if '```' in cleaned:
        # نشيل ```json و ``` و ` المفردة
        cleaned = re.sub(r'```\s*json', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace('```', '')
        cleaned = cleaned.strip()

    # طريقة 1: JSON مباشر بعد التنظيف
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # طريقة 2: المحاولة على النص الأصلي
    try:
        return json.loads(raw)
    except Exception:
        pass

    # طريقة 3: استخراج أول { وآخر } من النص المنظّف
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end+1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # طريقة 4: نفس الشي على النص الأصلي
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end+1])
        except Exception:
            pass

    # fallback: لو فشل كل شي، نعرض النص كرسالة بعد تنظيفه من أي backticks
    fallback_text = raw.replace('```json', '').replace('```', '').strip()
    result = dict(EMPTY)
    result["message"] = fallback_text
    return result

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
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
        print(f"❌ خطأ في /chat: {repr(e)}")
        parsed = dict(EMPTY)
        parsed["message"] = "عذراً، صار خلل بسيط. حاول مرة ثانية بعد لحظات. 🌱"
    return jsonify(parsed)

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    data = request.json or {}
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
        parsed["message"] = "⚠️ حدث خطأ في تحليل الصورة. حاول مرة أخرى."
    return jsonify(parsed)

if __name__ == '__main__':
    if not API_KEY:
        print("\n" + "="*60)
        print("⚠️  تنبيه: لم يتم العثور على المفتاح ANTHROPIC_API_KEY")
        print("افتح ملف env وضع مفتاحك بهذا الشكل:")
        print("ANTHROPIC_API_KEY=sk-ant-api03-...")
        print("="*60 + "\n")
    else:
        print("\n✅ تم تحميل المفتاح بنجاح. التطبيق جاهز!\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
