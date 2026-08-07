from app.main import app
from app.ai.model_loader import is_model_available
from app.services.ai_service import analyze_xray_image

print("app", app.title)
print("model", is_model_available())
print("ai_service", callable(analyze_xray_image))
