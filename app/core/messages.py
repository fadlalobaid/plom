"""Public API success and error messages (Arabic).

Keep client-facing copy here so endpoints stay consistent and easy to update.
Internal/log-only English strings may remain in services.
"""

# --- Success ---
PASSWORD_CHANGED = "تم تغيير كلمة المرور بنجاح"
PASSWORD_RESET = "تم إعادة تعيين كلمة المرور بنجاح"
LOGGED_OUT = "تم تسجيل الخروج بنجاح"

# --- Auth / access ---
INVALID_CREDENTIALS = "البريد الإلكتروني أو كلمة المرور غير صحيحة"
INVALID_SESSION = "انتهت صلاحية الجلسة أو تعذر التحقق منها. سجّل الدخول مجدداً"
INACTIVE_ACCOUNT = "الحساب غير نشط. يرجى التواصل مع المدير"
PASSWORD_CHANGE_REQUIRED = "يجب تغيير كلمة المرور قبل متابعة استخدام النظام"
ADMIN_REQUIRED = "هذه العملية متاحة لمدير النظام فقط"
CURRENT_PASSWORD_INCORRECT = "كلمة المرور الحالية غير صحيحة"
PASSWORD_REUSE_NOT_ALLOWED = "يجب أن تختلف كلمة المرور الجديدة عن الحالية"
PASSWORD_RESET_DOCTORS_ONLY = "إعادة تعيين كلمة المرور متاحة لحسابات الأطباء فقط"

# --- Resources not found ---
DOCTOR_NOT_FOUND = "الطبيب غير موجود"
PATIENT_NOT_FOUND = "المريض غير موجود"
XRAY_NOT_FOUND = "صورة الأشعة غير موجودة"
DIAGNOSIS_NOT_FOUND = "نتيجة التشخيص غير موجودة"

# --- Conflicts ---
EMAIL_ALREADY_EXISTS = "البريد الإلكتروني مستخدم مسبقاً"
NATIONAL_ID_ALREADY_EXISTS = "الرقم الوطني مستخدم مسبقاً"

# --- Diagnosis ---
XRAY_NOT_OWNED_BY_PATIENT = "صورة الأشعة لا تتبع المريض المحدد"
XRAY_STORAGE_PATH_MISSING = "مسار تخزين صورة الأشعة غير متوفر"
XRAY_NOT_ELIGIBLE_FOR_ANALYSIS = "صورة الأشعة غير صالحة للتحليل الآلي"
DIAGNOSIS_ALREADY_EXISTS = "توجد نتيجة تشخيص مسبقاً لهذه الصورة"
XRAY_UNAVAILABLE_FOR_ANALYSIS = "تعذر الحصول على صورة الأشعة للتحليل"
DIAGNOSIS_FAILED = "تعذر إكمال التحليل الآلي. حاول لاحقاً"
NO_POSITIVE_FINDINGS = (
    "لم تظهر في هذه الصورة مؤشرات واضحة لأي من الأمراض التي يفحصها النظام. "
    "هذه نتيجة مساعدة فقط ولا تغني عن تقييم الطبيب."
)

# --- X-ray upload / storage ---
INVALID_CHEST_XRAY = "الصورة المرفوعة ليست صورة أشعة صدر صالحة للتحليل"
XRAY_VALIDATION_UNAVAILABLE = "تعذر التحقق من صلاحية صورة الأشعة حالياً. حاول لاحقاً"
XRAY_STORAGE_UNAVAILABLE = "تعذر حفظ صورة الأشعة حالياً. حاول لاحقاً"
XRAY_STORAGE_DELETE_FAILED = "تعذر حذف صورة الأشعة من التخزين"
XRAY_SIGNED_URL_FAILED = "تعذر إنشاء رابط تحميل صورة الأشعة"
XRAY_LEGACY_LOCAL_NOT_SIGNABLE = "لا يمكن إنشاء رابط تحميل لملفات الأشعة المحلية القديمة"


def xray_file_too_large(max_bytes: int) -> str:
    """Return a size-limit message with the configured maximum."""
    return f"حجم الملف يتجاوز الحد الأقصى المسموح ({max_bytes} بايت)"
