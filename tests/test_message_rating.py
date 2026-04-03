"""
测试消息评分系统 - TDD 演示

功能：用户可以给 AI 消息打分（1-5 星）
流程：Red -> Green -> Refactor
"""

import pytest
from datetime import datetime
from typing import Optional


class TestMessageRating:
    """消息评分系统测试"""

    class TestCreateRating:
        """测试创建评分"""

        def test_create_rating_with_valid_score(self):
            """测试用有效分数创建评分"""
            from core.models.message import MessageRating

            rating = MessageRating(
                message_id="msg-001",
                score=5,
            )
            assert rating.message_id == "msg-001"
            assert rating.score == 5

        def test_create_rating_with_comment(self):
            """测试带评论的评分"""
            from core.models.message import MessageRating

            rating = MessageRating(
                message_id="msg-002",
                score=4,
                comment="很有帮助的回答",
            )
            assert rating.comment == "很有帮助的回答"

        def test_rating_score_must_be_between_1_and_5(self):
            """测试评分必须在 1-5 之间"""
            from core.models.message import MessageRating

            with pytest.raises(ValueError):
                MessageRating(message_id="msg-003", score=0)

            with pytest.raises(ValueError):
                MessageRating(message_id="msg-003", score=6)

        def test_rating_score_must_be_integer(self):
            """测试评分必须是整数 - Pydantic 会处理类型验证"""
            from core.models.message import MessageRating
            from pydantic import ValidationError

            # Pydantic 会尝试转换，但 3.5 不能转为 int
            with pytest.raises(ValidationError):
                MessageRating(message_id="msg-004", score=3.5)

        def test_rating_auto_generates_timestamp(self):
            """测试评分自动生成时间戳"""
            from core.models.message import MessageRating

            before = datetime.now().timestamp()
            rating = MessageRating(message_id="msg-005", score=3)
            after = datetime.now().timestamp()

            assert before <= rating.created_at <= after

        def test_rating_auto_generates_id(self):
            """测试评分自动生成 ID"""
            from core.models.message import MessageRating

            rating = MessageRating(message_id="msg-006", score=4)
            assert rating.id is not None
            assert len(rating.id) > 0

    class TestRatingValidation:
        """测试评分验证"""

        def test_rating_requires_message_id(self):
            """测试评分需要 message_id"""
            from core.models.message import MessageRating

            with pytest.raises(ValueError):
                MessageRating(message_id="", score=3)

        def test_rating_comment_max_length(self):
            """测试评论有最大长度限制"""
            from core.models.message import MessageRating

            long_comment = "a" * 1001  # 超过 1000 字符
            with pytest.raises(ValueError):
                MessageRating(
                    message_id="msg-007",
                    score=3,
                    comment=long_comment,
                )

    class TestRatingStatistics:
        """测试评分统计"""

        def test_calculate_average_score(self):
            """测试计算平均评分"""
            from core.models.message import calculate_average_rating

            ratings = [
                {"score": 5},
                {"score": 4},
                {"score": 3},
                {"score": 5},
                {"score": 4},
            ]
            avg = calculate_average_rating(ratings)
            assert avg == 4.2

        def test_calculate_empty_ratings(self):
            """测试空评分列表返回 None"""
            from core.models.message import calculate_average_rating

            avg = calculate_average_rating([])
            assert avg is None

        def test_rating_distribution(self):
            """测试评分分布统计"""
            from core.models.message import get_rating_distribution

            ratings = [
                {"score": 5},
                {"score": 5},
                {"score": 4},
                {"score": 3},
                {"score": 5},
            ]
            dist = get_rating_distribution(ratings)
            assert dist[5] == 3
            assert dist[4] == 1
            assert dist[3] == 1
            assert dist[2] == 0
            assert dist[1] == 0

    class TestRatingToDict:
        """测试评分序列化"""

        def test_rating_to_dict(self):
            """测试评分转换为字典"""
            from core.models.message import MessageRating

            rating = MessageRating(
                message_id="msg-008",
                score=5,
                comment="完美！",
            )
            data = rating.to_dict()

            assert data["message_id"] == "msg-008"
            assert data["score"] == 5
            assert data["comment"] == "完美！"
            assert "id" in data
            assert "created_at" in data

        def test_rating_from_dict(self):
            """测试从字典创建评分"""
            from core.models.message import MessageRating

            data = {
                "id": "rating-001",
                "message_id": "msg-009",
                "score": 4,
                "comment": "不错的回答",
                "created_at": 1234567890.0,
            }
            rating = MessageRating.from_dict(data)

            assert rating.id == "rating-001"
            assert rating.message_id == "msg-009"
            assert rating.score == 4
            assert rating.comment == "不错的回答"
            assert rating.created_at == 1234567890.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
