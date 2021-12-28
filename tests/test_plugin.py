class TestPlugin:
    def test_filter(self, mocker) -> None:
        mocker.get_one_reply("https://delta.chat")

        assert not mocker.get_replies("message without link")
