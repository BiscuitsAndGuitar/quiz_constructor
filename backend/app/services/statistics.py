from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from app.services.scoring import normalize_text


def rounded(value):
    return float(Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def percentage(numerator, denominator):
    return rounded(Decimal(str(numerator)) * 100 / Decimal(str(denominator))) if denominator else 0.0


def average(values):
    return rounded(sum(Decimal(str(value)) for value in values) / len(values)) if values else None


def median_seconds(durations):
    return int(median(durations)) if durations else None


def daily_counts(dates):
    counts = Counter(dates)
    if not counts:
        return []
    day, last = min(counts), max(counts)
    result = []
    while day <= last:
        result.append({'date': day.isoformat(), 'count': counts[day]})
        day += timedelta(days=1)
    return result


def grade_counts(scale, grade_ids):
    counts = Counter(grade_ids)
    return [{'grade': row['grade'], 'count': counts[row['id']]}
            for row in sorted(scale, key=lambda row: row['min_percent'])]


def top_answers(texts):
    counts = Counter(value for text in texts if (value := normalize_text(text)))
    return [{'value': value, 'count': count}
            for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]]


def question_statistics(question, rows, is_test):
    shown = len(rows)
    result = {'question_id': question['id'], 'text': question['text'], 'type': question['type'],
              'shown': shown, 'skipped': sum(not row['option_ids'] and not normalize_text(row['text']) for row in rows)}
    if is_test:
        maximum = question.get('points') or 0
        result.update(correct_percent=percentage(sum(row['score'] == maximum for row in rows), shown),
                      avg_score_percent=percentage(sum(row['score'] or 0 for row in rows), shown * maximum))
    if question['type'] == 'text':
        result['top_answers'] = top_answers(row['text'] for row in rows)
    else:
        # Один выбранный вариант учитывается не более одного раза в одном ответе.
        counts = Counter(option_id for row in rows for option_id in set(row['option_ids']))
        result['options'] = []
        for option in question['options']:
            item = {'option_id': option['id'], 'text': option['text'], 'count': counts[option['id']],
                    'percent': percentage(counts[option['id']], shown)}
            if is_test:
                item['is_correct'] = option['is_correct']
            result['options'].append(item)
    return result


def build_statistics(form, attempts, answers):
    """Все аргументы — обычные данные; запросов к БД и зависимости от FastAPI здесь нет."""
    completed = [attempt for attempt in attempts if attempt['finished_at'] is not None]
    completed_ids = {attempt['id'] for attempt in completed}
    by_question = defaultdict(list)
    for answer in answers:
        if answer['attempt_id'] in completed_ids:
            by_question[answer['question_id']].append(answer)
    is_test = form['is_test']
    rule_counts = Counter(attempt['early_finish_rule_id'] for attempt in completed)
    result = {
        'form': {key: form[key] for key in ['id', 'is_test', 'title']},
        'summary': {
            'started': len(attempts), 'finished': len(completed),
            'completion_percent': percentage(len(completed), len(attempts)),
            'finished_early': None if is_test else sum(a['early_finish_rule_id'] is not None for a in completed),
            'median_time_seconds': median_seconds([(a['finished_at'] - a['started_at']).total_seconds() for a in completed]),
            'avg_score': average([a['score'] for a in completed]) if is_test else None,
            'avg_percent': average([a['percent'] for a in completed]) if is_test else None,
        },
        'grade_distribution': grade_counts(form['grading_scale'], [a['grading_scale_id'] for a in completed]) if is_test else None,
        'early_finish_rules': None if is_test else [],
        'daily_finished': daily_counts([a['finished_at'].date() for a in completed]),
        'blocks': [] if is_test and len(form['blocks']) >= 2 else None,
        'questions': [],
    }
    for block in form['blocks']:
        questions = [q for q in block['questions'] if q['type'] != 'info']
        if result['blocks'] is not None:
            maximum = sum(q.get('points') or 0 for q in questions)
            score = sum(row['score'] or 0 for q in questions for row in by_question[q['id']])
            result['blocks'].append({'block_id': block['id'], 'title': block['title'], 'questions_count': len(questions),
                                     'max_points': maximum, 'avg_percent': percentage(score, len(completed) * maximum)})
        for question in questions:
            result['questions'].append(question_statistics(question, by_question[question['id']], is_test))
            if not is_test:
                for rule in question.get('finish_rules', []):
                    if rule_counts[rule['id']]:
                        result['early_finish_rules'].append({'rule_id': rule['id'], 'question_id': question['id'],
                            'question_text': question['text'], 'message': rule['message'], 'count': rule_counts[rule['id']]})
    return result
