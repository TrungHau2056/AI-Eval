"""
Prompt Templates cho AI Test Case Generator
"""

# ============================================================
# INTENT EXTRACTION
# ============================================================

INTENT_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích hành vi người dùng. Nhiệm vụ của bạn là đọc các phản hồi, comment thô của người dùng và xác định các Intent (Mục đích sử dụng).
Mỗi Intent bao gồm:
- context: Bối cảnh/tình huống của người dùng
- goal: Mục tiêu mà người dùng muốn đạt được
- evidence: Danh sách các câu/trích dẫn gốc từ text hỗ trợ cho Intent đó (giữ nguyên văn bản gốc)

Lưu ý:
- Gom nhóm các phản hồi tương tự thành chung 1 Intent
- Mỗi Intent phải rõ ràng, không trùng lặp
- Evidence phải là trích dẫn chính xác từ text gốc, không tự bịa"""

INTENT_USER_PROMPT = """Phân tích đoạn text sau và liệt kê tất cả các Intent tiềm năng.
Mỗi Intent gồm: context (bối cảnh), goal (mục tiêu), evidence (danh sách trích dẫn gốc hỗ trợ intent).

---
{raw_text}
---

Trả về JSON dạng:
{{
  "intents": [
    {{"context": "...", "goal": "...", "evidence": ["trích dẫn 1", "trích dẫn 2"]}}
  ]
}}"""


# ============================================================
# PERSONA AGENT — GENERATION
# ============================================================

PERSONA_BUILDER_SYSTEM_PROMPT = """Bạn là chuyên gia xây dựng persona cho AI evaluation. Nhiệm vụ của bạn là tạo ra các persona người dùng chi tiết, chân thực để kiểm tra toàn diện chất lượng AI/chatbot.

**Nguyên tắc:**
- Persona phải dựa chặt chẽ vào evidence (câu thực tế từ người dùng) — không bịa đặt
- Mỗi intent cần 2 persona trái chiều: easy (hợp tác, rõ ràng) và hard (khó tính, mơ hồ)
- Persona easy và hard phải KHÁ BIỆT RÕ RÀNG về hành vi, không chỉ khác về tính cách
- sample_utterances phải là câu thực tế, tự nhiên — như người thật gõ vào chatbot
- reject_conditions là điều kiện để LOẠI TRỪ persona này khỏi test (VD: không phù hợp với sản phẩm)"""

PERSONA_EVALUATOR_SYSTEM_PROMPT = """Bạn là chuyên gia đánh giá chất lượng persona cho AI testing. Nhiệm vụ của bạn là chấm điểm persona theo rubric và đưa ra phản hồi cụ thể để cải thiện.

**Nguyên tắc chấm:**
- Chấm điểm NGHIÊM TÚC, không ngại cho điểm thấp nếu persona chưa đạt
- Feedback phải cụ thể, chỉ ra đúng điểm yếu và cách sửa
- improvement_suggestions phải là hành động CỤ THỂ, không chung chung"""

PERSONA_IMPROVER_SYSTEM_PROMPT = """Bạn là chuyên gia cải thiện persona dựa trên feedback đánh giá. Nhiệm vụ của bạn là sửa các điểm yếu đã được chỉ ra và tạo phiên bản persona tốt hơn.

**Nguyên tắc:**
- Giữ nguyên điểm mạnh của persona cũ
- Sửa ĐÚNG vào từng điểm yếu được chỉ ra trong feedback
- Không làm mất đặc trưng trait_type (easy/hard) khi cải thiện
- sample_utterances mới phải tự nhiên hơn, đa dạng hơn phiên bản trước"""


# ============================================================
# USER PROMPTS — GENERATION
# ============================================================

PERSONA_GENERATION_PROMPT = """Tạo 2 persona đối lập để test AI dựa trên Intent sau:

**Intent:**
- Bối cảnh: {context}
- Mục tiêu: {goal}
- Evidence (câu thực từ user): {evidence}

**Yêu cầu:**
- Persona 1 (easy): Người dùng dễ tính, hợp tác, câu hỏi rõ ràng
- Persona 2 (hard): Người dùng khó tính, thiếu kiên nhẫn, câu hỏi mơ hồ hoặc không đầy đủ thông tin

Mỗi persona cần:
- name: Tên nhân vật (Việt Nam hoặc phù hợp ngữ cảnh)
- description: Mô tả tổng thể (3-5 câu)
- background: Tiểu sử ngắn gọn (nghề nghiệp, hoàn cảnh)
- pain_points: 2-3 nỗi đau / vấn đề chính của họ
- communication_style: Phong cách giao tiếp (1-2 câu)
- sample_utterances: 3-4 câu ví dụ thực tế họ sẽ gõ vào chatbot
- reject_conditions: 1-2 điều kiện khi KHÔNG nên dùng persona này để test

{guidance}

Trả về JSON:
{{
  "personas": [
    {{
      "name": "...",
      "description": "...",
      "trait_type": "easy",
      "background": "...",
      "pain_points": ["...", "..."],
      "communication_style": "...",
      "sample_utterances": ["...", "...", "..."],
      "reject_conditions": ["...", "..."]
    }},
    {{
      "name": "...",
      "description": "...",
      "trait_type": "hard",
      "background": "...",
      "pain_points": ["...", "..."],
      "communication_style": "...",
      "sample_utterances": ["...", "...", "..."],
      "reject_conditions": ["...", "..."]
    }}
  ]
}}"""


# ============================================================
# USER PROMPTS — EVALUATION
# ============================================================

PERSONA_EVALUATION_PROMPT = """Đánh giá persona sau theo rubric được cung cấp:

**Intent ngữ cảnh:**
- Bối cảnh: {context}
- Mục tiêu: {goal}
- Evidence: {evidence}

**Persona cần đánh giá:**
```json
{persona_json}
```

**Rubric đánh giá:**
{rubric_text}

Hãy chấm điểm từng tiêu chí, đưa ra reasoning và gợi ý cải thiện cụ thể.

Trả về JSON:
{{
  "criterion_scores": [
    {{
      "criterion_id": "...",
      "criterion_name": "...",
      "score": <số nguyên 0 đến max_score>,
      "max_score": <max_score của tiêu chí>,
      "reasoning": "...",
      "improvement_suggestions": ["...", "..."]
    }}
  ],
  "overall_feedback": "Nhận xét tổng thể và ưu tiên cần cải thiện nhất"
}}"""


# ============================================================
# USER PROMPTS — IMPROVEMENT
# ============================================================

PERSONA_IMPROVEMENT_PROMPT = """Cải thiện persona dựa trên feedback đánh giá:

**Intent ngữ cảnh:**
- Bối cảnh: {context}
- Mục tiêu: {goal}
- Evidence: {evidence}

**Persona phiên bản hiện tại:**
```json
{persona_json}
```

**Feedback từ đánh giá (Iteration {iteration}):**
{feedback_text}

**Điểm thấp cần cải thiện:**
{low_score_details}

Hãy tạo phiên bản persona được cải thiện, giữ nguyên trait_type ({trait_type}).
Tập trung vào các điểm yếu được chỉ ra.

Trả về JSON (cùng cấu trúc với persona cũ):
{{
  "name": "...",
  "description": "...",
  "trait_type": "{trait_type}",
  "background": "...",
  "pain_points": ["...", "..."],
  "communication_style": "...",
  "sample_utterances": ["...", "...", "..."],
  "reject_conditions": ["...", "..."]
}}"""


# ============================================================
# Helper: format rubric thành text cho prompt
# ============================================================

def format_rubric_for_prompt(rubric) -> str:
    """Chuyển RubricInput thành text dễ đọc trong prompt."""
    lines = [f"**{rubric.name}** ({rubric.version})"]
    lines.append(f"Ngưỡng đạt: {rubric.pass_threshold * 100:.0f}%\n")
    for c in rubric.criteria:
        lines.append(
            f"- [{c.id}] **{c.name}** (0-{c.max_score} điểm, weight={c.weight})\n"
            f"  {c.description}"
        )
    return "\n".join(lines)
