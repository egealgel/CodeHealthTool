def test_something():
    # test_ prefix → excluded from dead code report
    assert True


class TestStuff:
    def test_thing(self):
        assert True
