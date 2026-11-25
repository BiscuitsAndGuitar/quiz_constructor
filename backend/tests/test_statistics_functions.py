from datetime import date
from decimal import Decimal

import pytest

from app.services.statistics import (average, rounded, percentage, median_seconds, daily_counts,
                                     grade_counts, top_answers, build_statistics)


@pytest.mark.parametrize('values,expected', [([], None), ([7], 7), ([9, 2, 5], 5),
                                          ([9, 2], 5), ([1.2, 4.9], 3)])
def test_median(values, expected):
    assert median_seconds(values) == expected


def test_rounding_and_empty_averages():
    assert rounded(Decimal('1.25')) == 1.3
    assert percentage(1, 16) == 6.3
    assert percentage(1, 3) == 33.3
    assert percentage(0, 0) == 0
    assert average([]) is None
    assert average([Decimal('1.2'), Decimal('1.3')]) == 1.3


def test_days_and_grade_distribution():
    assert daily_counts([]) == []
    assert daily_counts([date(2026, 1, 3), date(2026, 1, 1), date(2026, 1, 3)]) == [
        {'date': '2026-01-01', 'count': 1}, {'date': '2026-01-02', 'count': 0}, {'date': '2026-01-03', 'count': 2}]
    scale = [{'id': 3, 'min_percent': 80, 'grade': '5'}, {'id': 1, 'min_percent': 0, 'grade': '2'}]
    assert grade_counts(scale, [3, None, 3]) == [{'grade': '2', 'count': 0}, {'grade': '5', 'count': 2}]
    assert grade_counts(scale, []) == [{'grade': '2', 'count': 0}, {'grade': '5', 'count': 0}]
    assert grade_counts([], [None]) == []


def test_text_normalization_sorting_and_limit():
    assert top_answers([' ДА  конечно ', 'да\nКОНЕЧНО', 'нет', ' ', None]) == [
        {'value': 'да конечно', 'count': 2}, {'value': 'нет', 'count': 1}]
    assert top_answers(['b', 'a', '1,5', '1.5']) == [
        {'value': '1,5', 'count': 1}, {'value': '1.5', 'count': 1}, {'value': 'a', 'count': 1}, {'value': 'b', 'count': 1}]
    assert len(top_answers([str(i) for i in range(25)])) == 20


def test_empty_statistics_ignores_info_and_keeps_empty_blocks():
    form = {'id': 1, 'title': 'Пустой', 'is_test': True, 'grading_scale': [], 'blocks': [
        {'id': 1, 'title': None, 'questions': [{'id': 1, 'type': 'info', 'points': 100}]},
        {'id': 2, 'title': None, 'questions': []}]}
    result = build_statistics(form, [], [])
    assert result['questions'] == [] and result['grade_distribution'] == []
    assert result['summary']['started'] == 0 and result['summary']['completion_percent'] == 0
    assert result['summary']['avg_score'] is None
    assert all(b['questions_count'] == b['max_points'] == b['avg_percent'] == 0 for b in result['blocks'])
