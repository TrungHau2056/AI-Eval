"""
Default Rubric cho Persona Evaluation
=======================================
Researcher có thể:
  1. Dùng rubric mặc định này
  2. Load từ file JSON: RubricInput.model_validate(json.load(...))
  3. Override từng tiêu chí qua CLI argument

Rubric này lấy cảm hứng từ rubric nội bộ của team (persona-research-rubric-v0.1)
nhưng được điều chỉnh cho agent loop tự động.
"""
from ..schemas.models import RubricCriterion, RubricInput


def get_default_rubric() -> RubricInput:
    """
    Rubric mặc định với 5 tiêu chí chính.
    Trọng số và ngưỡng có thể điều chỉnh qua file config.
    """
    return RubricInput(
        name="Persona Quality Rubric",
        version="v0.1",
        pass_threshold=0.70,  # 70% để pass
        criteria=[
            RubricCriterion(
                id="C1",
                name="Tính chân thực (Authenticity)",
                description=(
                    "Persona có đặc điểm, hành vi thực tế dựa trên evidence không? "
                    "sample_utterances có tự nhiên như người thật không?"
                ),
                weight=1.5,
                max_score=3,
            ),
            RubricCriterion(
                id="C2",
                name="Sự khác biệt easy/hard (Contrast)",
                description=(
                    "Persona easy và hard có KHÁ BIỆT RÕ RÀNG về hành vi giao tiếp không? "
                    "Không chỉ khác về mô tả tính cách mà phải khác trong cách đặt câu hỏi."
                ),
                weight=1.5,
                max_score=3,
            ),
            RubricCriterion(
                id="C3",
                name="Độ bao phủ Intent (Intent Coverage)",
                description=(
                    "Persona có phản ánh đúng context và goal của Intent không? "
                    "sample_utterances có liên quan trực tiếp đến intent không?"
                ),
                weight=1.0,
                max_score=3,
            ),
            RubricCriterion(
                id="C4",
                name="Reject Conditions (Điều kiện loại trừ)",
                description=(
                    "Persona có định nghĩa rõ điều kiện khi KHÔNG nên dùng không? "
                    "reject_conditions có cụ thể và hữu ích cho việc lọc test case không?"
                ),
                weight=1.0,
                max_score=3,
            ),
            RubricCriterion(
                id="C5",
                name="Tính khả dụng (Test Utility)",
                description=(
                    "Dùng persona này có thể tạo ra test case có giá trị không? "
                    "Có khả năng phát hiện edge case hoặc behavior bất thường của AI không?"
                ),
                weight=1.0,
                max_score=3,
            ),
        ],
    )
