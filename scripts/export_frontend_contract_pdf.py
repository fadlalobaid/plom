"""Export PulmoScan frontend data-contract PDF (tables, fields, validations)."""

from __future__ import annotations

import sys
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BACKEND_ROOT / "docs" / "PulmoScan_Frontend_Data_Contract.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\tahoma.ttf")
FONT_BOLD_PATH = Path(r"C:\Windows\Fonts\tahomabd.ttf")


def ar(text: str) -> str:
    """Reshape Arabic text for correct RTL display in PDF."""
    return get_display(arabic_reshaper.reshape(text))


class ContractPDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Tahoma", "", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, ar("PulmoScan عقد البيانات والتحقق للواجهة الامامية"), align="R")
        self.ln(4)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Tahoma", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"{self.page_no()}/{{nb}}", align="C")

    def section(self, title: str) -> None:
        self.ln(3)
        self.set_x(10)
        self.set_font("Tahoma", "B", 14)
        self.set_text_color(20, 60, 100)
        self.multi_cell(190, 8, ar(title), align="R")
        self.set_draw_color(20, 60, 100)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def subsection(self, title: str) -> None:
        self.ln(2)
        self.set_x(10)
        self.set_font("Tahoma", "B", 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(190, 7, ar(title), align="R")
        self.set_text_color(0, 0, 0)

    def body(self, text: str, *, size: int = 10) -> None:
        self.set_x(10)
        self.set_font("Tahoma", "", size)
        self.multi_cell(190, 6, ar(text), align="R")

    def bullet(self, text: str) -> None:
        self.set_x(10)
        self.set_font("Tahoma", "", 10)
        self.multi_cell(190, 6, ar(f"- {text}"), align="R")

    def _fit(self, text: str, width: float) -> str:
        display = ar(text) if _has_arabic(text) else text
        if self.get_string_width(display) <= width - 1.5:
            return display
        ellipsis = "..."
        while display and self.get_string_width(display + ellipsis) > width - 1.5:
            display = display[:-1]
        return display + ellipsis

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> None:
        def draw_header() -> None:
            self.set_x(10)
            self.set_font("Tahoma", "B", 8)
            self.set_fill_color(20, 60, 100)
            self.set_text_color(255, 255, 255)
            for header, width in zip(headers, col_widths, strict=True):
                self.cell(width, 7, self._fit(header, width), border=1, align="C", fill=True)
            self.ln()
            self.set_text_color(0, 0, 0)
            self.set_font("Tahoma", "", 7)

        draw_header()
        fill = False
        for row in rows:
            if self.get_y() > 275:
                self.add_page()
                draw_header()
            self.set_x(10)
            self.set_fill_color(248, 250, 252)
            for value, width in zip(row, col_widths, strict=True):
                display = self._fit(value, width)
                align = "R" if _has_arabic(value) else "L"
                self.cell(width, 6.5, display, border=1, align=align, fill=fill)
            self.ln()
            fill = not fill


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def build_pdf() -> Path:
    if not FONT_PATH.exists():
        raise SystemExit(f"Arabic-capable font not found: {FONT_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    pdf = ContractPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("Tahoma", "", str(FONT_PATH))
    if FONT_BOLD_PATH.exists():
        pdf.add_font("Tahoma", "B", str(FONT_BOLD_PATH))
    else:
        pdf.add_font("Tahoma", "B", str(FONT_PATH))

    # Cover
    pdf.add_page()
    pdf.set_x(10)
    pdf.ln(35)
    pdf.set_font("Tahoma", "B", 22)
    pdf.set_text_color(20, 60, 100)
    pdf.cell(0, 12, ar("عقد البيانات والتحقق"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Tahoma", "B", 16)
    pdf.cell(0, 10, ar("للواجهة الامامية Flutter"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Tahoma", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, "PulmoScan Backend API Data Contract", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, ar("الجداول والحقول وقواعد التحقق واكواد الحالة"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Tahoma", "", 10)
    pdf.cell(0, 6, "Base URL: /api/v1  |  Auth: Bearer JWT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, ar("مدة التوكن: 30 دقيقة"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_fill_color(240, 245, 250)
    pdf.set_font("Tahoma", "", 10)
    pdf.set_x(10)
    pdf.multi_cell(
        190,
        7,
        ar(
            "هذا الملف مرجع للفرونت لضمان تطابق النماذج والتحقق مع الباكند. "
            "اسماء الحقول بالانجليزية كما في الـ API، ووصف القواعد بالعربية."
        ),
        fill=True,
        align="R",
    )

    # Shared validation
    pdf.add_page()
    pdf.section("1) قواعد التحقق المشتركة")
    pdf.table(
        ["الحقل / النوع", "القاعدة", "ملاحظات"],
        [
            ["الاسم الشخصي", "2–100 حرف، حروف فقط (عربي/إنجليزي)", "مسافات و . ' - مسموحة. بدون أرقام"],
            ["full_name (طبيب)", "2–255 حرف بنفس قواعد الاسم", "مطلوب"],
            ["البريد email", "strip + lowercase + EmailStr", "فريد للطبيب"],
            ["الهاتف phone_number", "10 ارقام بالضبط", "مثال: 0912345678 بدون +"],
            ["الرقم الوطني national_id", "ارقام فقط طول 10-50", "فريد تعارض = 409"],
            ["تاريخ الميلاد", "الزامي ليس مستقبلا سنة >= 1900", "صيغة date"],
            ["المحافظة governorate", "قيمة عربية من التعداد فقط", "انظر القسم 4"],
            ["المنطقة area", "نص غير فارغ حد اقصى 255", "مطلوب"],
            ["التخصص specialization", "نص غير فارغ حد اقصى 255", "مطلوب للطبيب"],
            ["الشهادة certificate", "اختياري حد اقصى 500", "-"],
            ["ملاحظات notes", "اختياري حد اقصى 2000", "للاشعة"],
            ["كلمة المرور (انشاء/تغيير)", "8-128 حرف + رقم", "StrongPassword"],
            ["بحث SearchQuery", "strip غير فارغ حد 100", "query params"],
            ["حجم صورة الاشعة", "حد اقصى 10 MB", "تجاوز = 413"],
            ["امتداد الاشعة", ".jpg .jpeg .png .dcm", "نوع غير مدعوم = 400"],
        ],
        [45, 80, 65],
    )

    # Tables
    pdf.add_page()
    pdf.section("2) جداول قاعدة البيانات والحقول")

    pdf.subsection("2.1 جدول users (كلاس Python: Doctor — مسار API: /doctors)")
    pdf.table(
        ["الحقل", "النوع", "مطلوب؟", "التحقق / القيود"],
        [
            ["id", "UUID", "نعم (PK)", "يُولَّد تلقائياً"],
            ["full_name", "String(255)", "نعم", "اسم شخصي 2–255"],
            ["email", "String(255)", "نعم", "بريد صالح + فريد"],
            ["password_hash", "String(255)", "نعم", "لا يُرجع في الـ API"],
            ["specialization", "String(255)", "نعم", "غير فارغ ≤255"],
            ["date_of_birth", "Date", "نعم", "ليس مستقبلاً، سنة ≥1900"],
            ["national_id", "String(50)", "لا", "إن وُجد: أرقام 10–50 + فريد"],
            ["certificate", "String(500)", "لا", "≤500"],
            ["phone_number", "String(10)", "نعم", "10 أرقام"],
            ["governorate", "Enum", "نعم", "محافظة سورية عربية"],
            ["area", "String(255)", "نعم", "غير فارغ ≤255"],
            ["role", "Enum", "نعم", "admin | doctor"],
            ["status", "Enum", "نعم", "active | inactive"],
            ["must_change_password", "Boolean", "نعم", "true بعد إنشاء/إعادة تعيين"],
            ["created_at / updated_at", "DateTime(tz)", "نعم", "تلقائي"],
        ],
        [48, 35, 25, 82],
    )

    pdf.subsection("2.2 جدول patients")
    pdf.table(
        ["الحقل", "النوع", "مطلوب؟", "التحقق / القيود"],
        [
            ["id", "UUID", "نعم (PK)", "تلقائي"],
            ["first_name", "String(255)", "نعم", "اسم 2–100"],
            ["father_name", "String(255)", "نعم", "اسم 2–100"],
            ["mother_name", "String(255)", "نعم", "اسم 2–100"],
            ["last_name", "String(255)", "نعم", "اسم 2–100"],
            ["date_of_birth", "Date", "نعم", "ليس مستقبلاً"],
            ["gender", "Enum", "نعم", "male | female | other"],
            ["phone_number", "String(10)", "لا", "إن وُجد: 10 أرقام"],
            ["governorate", "Enum", "نعم", "محافظة عربية"],
            ["area", "String(255)", "نعم", "غير فارغ ≤255"],
            ["national_id", "String(50)", "نعم", "أرقام 10–50 + فريد"],
            ["created_by_doctor_id", "UUID FK→users", "نعم", "يُضبط من التوكن"],
            ["created_at / updated_at", "DateTime(tz)", "نعم", "تلقائي"],
        ],
        [48, 40, 25, 77],
    )
    pdf.body("ملاحظة: لا يوجد full_name ولا address في المريض بعد إعادة الهيكلة.")

    pdf.add_page()
    pdf.subsection("2.3 جدول xray_images")
    pdf.table(
        ["الحقل", "النوع", "مطلوب؟", "التحقق / القيود"],
        [
            ["id", "UUID", "نعم", "تلقائي"],
            ["patient_id", "UUID FK→patients", "نعم", "يجب أن يملكه الطبيب الحالي"],
            ["doctor_id", "UUID FK→users", "نعم", "من التوكن"],
            ["image_path", "String(500)", "نعم", "مسار التخزين على السيرفر"],
            ["taken_at", "DateTime(tz)", "لا", "اختياري"],
            ["result", "String(100)", "لا", "اختياري"],
            ["view_type", "Enum", "نعم", "pa | ap | lateral"],
            ["notes", "Text", "لا", "≤2000"],
            ["uploaded_at", "DateTime(tz)", "نعم", "تلقائي"],
            ["created_at / updated_at", "DateTime(tz)", "نعم", "تلقائي"],
        ],
        [42, 45, 22, 81],
    )

    pdf.subsection("2.4 جدول diagnosis_results")
    pdf.table(
        ["الحقل", "النوع", "مطلوب؟", "التحقق / القيود"],
        [
            ["id", "UUID", "نعم", "تلقائي"],
            ["patient_id", "UUID FK", "نعم", "مرتبط بمريض الطبيب"],
            ["doctor_id", "UUID FK", "نعم", "من التوكن"],
            ["xray_image_id", "UUID FK فريد", "نعم", "تشخيص واحد لكل صورة"],
            ["predicted_label", "String(100)", "نعم", "1–100"],
            ["confidence_score", "Numeric(6,5)", "نعم", "0 ≤ قيمة ≤ 1"],
            ["model_version", "String(50)", "نعم", "1–50"],
            ["report_text", "Text", "لا", "اختياري"],
            ["visual_map_path", "String(500)", "لا", "≤500"],
            ["created_at / updated_at", "DateTime(tz)", "نعم", "تلقائي"],
        ],
        [42, 40, 22, 86],
    )

    pdf.subsection("2.5 جدول audit_logs (عرض أدمن فقط)")
    pdf.table(
        ["الحقل", "النوع", "مطلوب؟", "ملاحظات"],
        [
            ["id", "UUID", "نعم", "تلقائي"],
            ["user_id", "UUID FK→users", "لا", "قد يكون null"],
            ["action", "Enum", "نعم", "LOGIN, CREATE_PATIENT, ..."],
            ["entity_type", "String(100)", "لا", "Doctor / Patient / ..."],
            ["entity_id", "UUID", "لا", "معرّف الكيان"],
            ["details", "JSON", "لا", "تفاصيل إضافية"],
            ["ip_address", "String(45)", "لا", "اختياري"],
            ["created_at", "DateTime(tz)", "نعم", "بدون updated_at"],
        ],
        [40, 40, 22, 88],
    )

    # Request schemas
    pdf.add_page()
    pdf.section("3) نماذج الطلب (Request Schemas) للفرونت")

    pdf.subsection("3.1 Auth")
    pdf.table(
        ["المخطط", "الحقول", "التحقق"],
        [
            ["LoginRequest", "email, password", "email مطبّع؛ password طول 8–128"],
            ["ChangePasswordRequest", "current_password, new_password", "current ≥1؛ new = StrongPassword"],
            ["TokenResponse", "access_token, token_type, must_change_password", "token_type=bearer"],
        ],
        [50, 70, 70],
    )

    pdf.subsection("3.2 DoctorCreate / DoctorUpdate")
    pdf.table(
        ["الحقل", "Create", "Update", "التحقق"],
        [
            ["full_name", "مطلوب", "اختياري*", "اسم 2–255"],
            ["email", "مطلوب", "اختياري*", "بريد صالح"],
            ["specialization", "مطلوب", "اختياري*", "≤255"],
            ["date_of_birth", "مطلوب", "اختياري*", "ليس مستقبلاً"],
            ["national_id", "اختياري", "اختياري", "أرقام 10–50"],
            ["certificate", "اختياري", "اختياري", "≤500"],
            ["phone_number", "مطلوب", "اختياري*", "10 أرقام"],
            ["governorate", "مطلوب", "اختياري*", "تعداد عربي"],
            ["area", "مطلوب", "اختياري*", "≤255"],
            ["password", "مطلوب", "اختياري*", "StrongPassword"],
            ["status", "—", "اختياري*", "active|inactive"],
        ],
        [40, 30, 30, 90],
    )
    pdf.body("* في PATCH: إرسال null صريح مرفوض للحقول الإلزامية (ما عدا national_id/certificate).")

    pdf.subsection("3.3 PatientCreate / PatientUpdate")
    pdf.table(
        ["الحقل", "Create", "Update", "التحقق"],
        [
            ["first_name", "مطلوب", "اختياري*", "اسم 2–100"],
            ["father_name", "مطلوب", "اختياري*", "اسم 2–100"],
            ["mother_name", "مطلوب", "اختياري*", "اسم 2–100"],
            ["last_name", "مطلوب", "اختياري*", "اسم 2–100"],
            ["date_of_birth", "مطلوب", "اختياري*", "ليس مستقبلاً"],
            ["gender", "مطلوب", "اختياري*", "male|female|other"],
            ["phone_number", "اختياري", "اختياري (يمكن null)", "10 أرقام إن وُجد"],
            ["governorate", "مطلوب", "اختياري*", "تعداد عربي"],
            ["area", "مطلوب", "اختياري*", "≤255"],
            ["national_id", "مطلوب", "اختياري*", "أرقام 10–50 + فريد"],
        ],
        [40, 35, 45, 70],
    )
    pdf.body("ملاحظة بحث المرضى: query باسم full_name يبحث داخل حقول الاسم المفككة (وليس عمود full_name).")

    pdf.subsection("3.4 رفع الأشعة (multipart) — ليس JSON")
    pdf.table(
        ["الحقل", "مطلوب؟", "التحقق"],
        [
            ["patient_id", "نعم", "UUID"],
            ["view_type", "نعم", "pa | ap | lateral"],
            ["file", "نعم", "jpg/jpeg/png/dcm ≤10MB"],
            ["notes", "لا", "≤2000"],
            ["taken_at", "لا", "datetime اختياري"],
        ],
        [45, 30, 115],
    )

    pdf.subsection("3.5 DiagnosisAnalysisRequest")
    pdf.table(
        ["الحقل", "مطلوب؟", "التحقق"],
        [
            ["patient_id", "نعم", "UUID"],
            ["xray_image_id", "نعم", "UUID — صورة بلا تشخيص سابق"],
        ],
        [50, 30, 110],
    )

    # Enums
    pdf.add_page()
    pdf.section("4) التعدادات (Enums) — القيم النصية الدقيقة")
    pdf.subsection("4.1 تعدادات عامة")
    pdf.table(
        ["التعداد", "القيم"],
        [
            ["DoctorRole", "admin , doctor"],
            ["DoctorStatus", "active , inactive"],
            ["Gender", "male , female , other"],
            ["XrayViewType", "pa , ap , lateral"],
            [
                "AuditAction",
                "LOGIN LOGOUT CREATE/UPDATE/DELETE_DOCTOR",
            ],
            [
                "AuditAction (2)",
                "CREATE/UPDATE/DELETE_PATIENT UPLOAD/DELETE_XRAY",
            ],
            [
                "AuditAction (3)",
                "CREATE_DIAGNOSIS CHANGE_PASSWORD",
            ],
            ["AuditEntityType", "Doctor , Patient , XrayImage , DiagnosisResult"],
        ],
        [45, 145],
    )

    pdf.subsection("4.2 المحافظات السورية — أرسل/استقبل هذه النصوص العربية حرفياً")
    pdf.table(
        ["المفتاح (مرجع)", "القيمة في الـ API"],
        [
            ["IDLIB", "إدلب"],
            ["AL_HASAKAH", "الحسكة"],
            ["ALEPPO", "حلب"],
            ["HAMA", "حماة"],
            ["HOMS", "حمص"],
            ["DAMASCUS", "دمشق"],
            ["DARA", "درعا"],
            ["DEIR_EZ_ZOR", "دير الزور"],
            ["AL_RAQQAH", "الرقة"],
            ["RIF_DIMASHQ", "ريف دمشق"],
            ["AS_SUWAYDA", "السويداء"],
            ["TARTOUS", "طرطوس"],
            ["AL_QUNEITRA", "القنيطرة"],
            ["LATAKIA", "اللاذقية"],
        ],
        [60, 130],
    )

    # Endpoints
    pdf.add_page()
    pdf.section("5) نقاط الـ API الأساسية")
    pdf.table(
        ["Method", "Path", "الصلاحية", "Body"],
        [
            ["POST", "/auth/login", "عام", "LoginRequest"],
            ["GET", "/auth/me", "Active", "—"],
            ["POST", "/auth/change-password", "Active", "ChangePasswordRequest"],
            ["POST", "/auth/logout", "Active", "—"],
            ["POST", "/doctors/", "Admin", "DoctorCreate"],
            ["GET", "/doctors/", "Admin", "—"],
            ["PATCH", "/doctors/{id}", "Admin", "DoctorUpdate"],
            ["DELETE", "/doctors/{id}", "Admin", "تعطيل (soft)"],
            ["POST", "/patients/", "PasswordOK", "PatientCreate"],
            ["GET", "/patients/", "PasswordOK", "query بحث اختياري"],
            ["PATCH", "/patients/{id}", "PasswordOK", "PatientUpdate"],
            ["DELETE", "/patients/{id}", "PasswordOK", "204"],
            ["POST", "/xray-images/upload", "PasswordOK", "multipart"],
            ["POST", "/diagnosis/analyze", "PasswordOK", "DiagnosisAnalysisRequest"],
            ["GET", "/statistics/overview", "Admin", "—"],
            ["GET", "/audit-logs/", "Admin", "فلاتر + pagination"],
        ],
        [22, 58, 35, 75],
    )
    pdf.body(
        "PasswordOK = JWT صالح + حساب نشط + إن كان doctor و must_change_password=true "
        "فيرفض المسارات السريرية بـ 403 حتى تغيير كلمة المرور."
    )

    # Status codes
    pdf.section("6) أكواد الحالة المهمة للفرونت")
    pdf.table(
        ["الكود", "المعنى"],
        [
            ["422", "فشل تحقق Pydantic/الحقول (اسم، هاتف، تعداد، بريد...)"],
            ["400", "خطأ منطقي: كلمة مرور خاطئة، نوع ملف غير مدعوم، تشخيص مكرر..."],
            ["401", "توكن مفقود/غير صالح أو بيانات دخول خاطئة"],
            ["403", "غير أدمن / حساب غير نشط / مطلوب تغيير كلمة المرور"],
            ["404", "الكيان غير موجود أو لا يخص الطبيب الحالي"],
            ["409", "تعارض فريد: email أو national_id موجود مسبقاً"],
            ["413", "ملف الأشعة أكبر من 10MB"],
            ["201", "إنشاء ناجح (طبيب/مريض/أشعة/تشخيص)"],
            ["204", "حذف ناجح"],
        ],
        [25, 165],
    )

    # Flutter checklist
    pdf.section("7) قائمة تحقق سريعة لـ Flutter")
    for item in [
        "الهاتف دائماً 10 أرقام محلية مثل 0912345678 — بدون +963.",
        "المحافظة يجب أن تُرسل كنص عربي مطابق للتعداد (دمشق وليس DAMASCUS).",
        "المريض يستخدم first/father/mother/last name وليس full_name/address.",
        "رفع الأشعة عبر multipart/form-data وليس JSON.",
        "بعد login إذا must_change_password=true للمريض/الطبيب العادي → شاشة تغيير كلمة المرور إلزامية.",
        "بعد change-password يُبطَل التوكن الحالي → إعادة login.",
        "اعرض أخطاء 422 من detail ورسائل 409/413 للمستخدم بشكل واضح.",
        "Authorization: Bearer <access_token> لكل المسارات المحمية.",
    ]:
        pdf.bullet(item)

    pdf.ln(6)
    pdf.set_font("Tahoma", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(10)
    pdf.cell(
        190,
        5,
        ar("تم التوليد تلقائيا من مواصفات Backend الحالية لمشروع PulmoScan."),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.output(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    path = build_pdf()
    print(f"PDF exported: {path}")
