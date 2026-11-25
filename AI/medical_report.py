"""
AI/medical_report.py
---------------------
Feature 5: AI medical report summarization.

IMPORTANT DISCLAIMER (also shown in the GUI):
This feature is FOR INFORMATIONAL PURPOSES ONLY. It does not provide medical
advice, diagnosis, or treatment. Users must always consult a qualified
doctor. WheelGuide and its AI summary are not a substitute for professional
medical judgement.
"""

import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


DISCLAIMER = (
    "\u26A0 DISCLAIMER: This is an AI-generated summary for informational "
    "purposes only. It is NOT medical advice, diagnosis, or treatment. "
    "Please consult a qualified doctor about your medical report."
)


def _configure_gemini():
    if not GEMINI_AVAILABLE:
        return False
    if not GEMINI_API_KEY or "PASTE_YOUR" in GEMINI_API_KEY:
        return False
    genai.configure(api_key=GEMINI_API_KEY)
    return True


def summarize_report(report_text: str) -> str:
    """
    Takes raw medical report text (already extracted from a PDF/scan by the
    user or another tool) and returns a plain-language summary.
    Always prepends the disclaimer.
    """
    if not report_text or not report_text.strip():
        return DISCLAIMER + "\n\nNo report text was provided to summarize."

    if _configure_gemini():
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
You are helping a patient understand their medical report in simple,
plain language. You are NOT a doctor and must not give a diagnosis,
prescribe treatment, or tell the user what to do medically. Only explain,
in simple terms, what the report says, and suggest the patient discuss any
concerns with their doctor.

Medical report text:
\"\"\"{report_text}\"\"\"

Write a short, clear, plain-language summary (max 200 words) of what this
report says. End with: "Please discuss this report with your doctor for
medical advice."
"""
            response = model.generate_content(prompt)
            summary = response.text.strip()
            return f"{DISCLAIMER}\n\n{summary}"
        except Exception as e:
            print(f"[medical_report.py] Gemini summarization failed: {e}")

    # Offline fallback — extractive mini-summary (first + key sentences)
    return f"{DISCLAIMER}\n\n{_offline_fallback_summary(report_text)}"


def _offline_fallback_summary(report_text: str) -> str:
    """Very simple offline fallback: pick sentences containing common
    medical-report keywords so the feature still works with no internet."""
    keywords = ["diagnosis", "impression", "finding", "recommend",
                "advice", "result", "abnormal", "normal", "follow up",
                "follow-up"]
    sentences = re.split(r'(?<=[.!?])\s+', report_text.strip())
    picked = [s for s in sentences if any(k in s.lower() for k in keywords)]
    if not picked:
        picked = sentences[:3]
    summary = " ".join(picked[:5])
    return (
        "Offline mode summary (no AI available):\n" + summary +
        "\n\nPlease discuss this report with your doctor for medical advice."
    )


if __name__ == "__main__":
    sample = ("Patient presents with mild lower back pain. X-ray findings: "
               "no fracture detected. Impression: muscular strain. "
               "Recommend physiotherapy and follow-up in 2 weeks.")
    print(summarize_report(sample))
