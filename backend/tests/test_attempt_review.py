from test_attempts import published, start, finish
from test_forms import headers, users


def test_review_option_texts_keep_form_order(client, users):
    form = published(client, users, True)
    started = start(client, form, users[2])
    questions = [q for block in form['blocks'] for q in block['questions']]
    answers = [{'question_id': int(q['key'][1:]),
                'option_ids': [int(o['key'][1:]) for o in reversed(q['options'])]}
               for q in questions if q['type'] == 'multiple']
    response = finish(client, started, answers, users[2])
    assert response.status_code == 200
    result = response.json()
    assert client.get(f"/attempts/{started['attempt']['id']}/result", headers=headers(users[2])).json() == result
    for question, review in zip(questions, result['review']):
        if question['type'] == 'text':
            assert 'your_options' not in review and 'correct_options' not in review
            continue
        options = [{'id': int(o['key'][1:]), 'text': o['text']} for o in question['options']]
        assert review['your_options'] == (options if question['type'] == 'multiple' else [])
        assert review['correct_options'] == [o for o, source in zip(options, question['options']) if source['is_correct']]
        assert {o['id'] for o in review['your_options']} == set(review['your_option_ids'])
        assert [o['id'] for o in review['correct_options']] == review['correct_option_ids']
