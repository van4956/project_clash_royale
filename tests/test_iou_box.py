import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from modules.iou_box import iou_box


# Фикстура с тестовыми данными
@pytest.fixture
def arg_boxes():
    """Подготовка тестовых боксов"""
    return {
        'box_1': (0, 10, 10, 0),
        'box_2': (5, 10, 15, 0),
        'box_3': (10, 10, 20, 0),
        'box_4': (5, 20, 25, 0),
        'box_5': (130, 20, 150, 0),
        'box_6': (30, 10, 40, 0),
        'box_7': (130, 10, 140, 0),
    }


def test_identical_boxes(arg_boxes):
    """Тест: идентичные боксы должны давать IoU = 1.0"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_1'])
    assert result == pytest.approx(1.0, abs=0.01)


def test_overlapping_boxes(arg_boxes):
    """Тест: частично перекрывающиеся боксы (box_1 и box_2)"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_2'])
    expected = 0.33
    assert result == pytest.approx(expected, abs=0.1)


def test_touching_boxes(arg_boxes):
    """Тест: боксы, соприкасающиеся краями (box_1 и box_3)"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_3'])
    # При касании только краем IoU должен быть близок к 0
    assert result < 0.1


def test_distant_boxes_horizontal(arg_boxes):
    """Тест: удаленные боксы по горизонтали (box_1 и box_6)"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_6'])
    assert result < 0.5


def test_very_distant_boxes_horizontal(arg_boxes):
    """Тест: очень удаленные боксы по горизонтали (box_1 и box_7)"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_7'])
    assert result < 0.1


def test_distant_boxes_vertical(arg_boxes):
    """Тест: удаленные боксы по вертикали (box_1 и box_4)"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_4'])
    assert result < 0.5


def test_very_distant_boxes_diagonal(arg_boxes):
    """Тест: очень удаленные боксы по диагонали (box_1 и box_5)"""
    result = iou_box(arg_boxes['box_1'], arg_boxes['box_5'])
    assert result < 0.1


def test_symmetry(arg_boxes):
    """Тест: IoU должен быть симметричным (IoU(A,B) = IoU(B,A))"""
    result_ab = iou_box(arg_boxes['box_1'], arg_boxes['box_2'])
    result_ba = iou_box(arg_boxes['box_2'], arg_boxes['box_1'])
    assert result_ab == result_ba


def test_with_custom_alpha(arg_boxes):
    """Тест: проверка работы с параметром alpha"""
    result_alpha_1 = iou_box(arg_boxes['box_1'], arg_boxes['box_2'], alpha=1.0)
    result_alpha_0 = iou_box(arg_boxes['box_1'], arg_boxes['box_2'], alpha=0.0)
    # При разных alpha результаты должны отличаться
    assert result_alpha_1 != result_alpha_0


# Параметризованный тест (бонус - демонстрация мощи pytest)
@pytest.mark.parametrize("box_pair,expected_low", [
    (('box_1', 'box_6'), True),  # удаленные по горизонтали
    (('box_1', 'box_7'), True),  # очень удаленные по горизонтали
    (('box_1', 'box_4'), True),  # удаленные по вертикали
    (('box_1', 'box_5'), True),  # очень удаленные по диагонали
    (('box_1', 'box_2'), False), # перекрывающиеся
])
def test_distance_cases(arg_boxes, box_pair, expected_low):
    """Параметризованный тест для разных случаев расстояния между боксами"""
    box_a_key, box_b_key = box_pair
    result = iou_box(arg_boxes[box_a_key], arg_boxes[box_b_key])
    if expected_low:
        assert result < 0.5, f"IoU для {box_pair} должен быть низким"
    else:
        assert result >= 0.2, f"IoU для {box_pair} должен быть выше"
