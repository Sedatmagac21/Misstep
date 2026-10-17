from misstep.vision import parse_response


def test_parse_response_keeps_lines_and_clamps_confidence():
    lines = parse_response('{"lines":[{"text":"3x-(x+3)=7","confidence":0.9},{"text":" ","confidence":1},{"text":"x=2","confidence":1.4}]}')
    assert [l.text for l in lines] == ["3x-(x+3)=7", "x=2"]
    assert lines[1].confidence == 1.0
