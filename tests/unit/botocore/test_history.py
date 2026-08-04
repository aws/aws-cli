from botocore.history import (
    BaseHistoryHandler,
    HistoryRecorder,
    get_global_history_recorder,
)
from tests import mock, unittest


class TerribleError(Exception):
    pass


class ExceptionThrowingHandler(BaseHistoryHandler):
    def emit(self, event_type, payload, source):
        raise TerribleError('Bad behaving handler')


class TestHistoryRecorder(unittest.TestCase):
    def test_can_attach_and_call_handler_emit(self):
        mock_handler = mock.Mock(spec=BaseHistoryHandler)
        recorder = HistoryRecorder()
        recorder.enable()
        recorder.add_handler(mock_handler)
        recorder.record('foo', 'bar', source='source')

        mock_handler.emit.assert_called_with('foo', 'bar', 'source')

    def test_can_call_multiple_handlers(self):
        first_handler = mock.Mock(spec=BaseHistoryHandler)
        second_handler = mock.Mock(spec=BaseHistoryHandler)
        recorder = HistoryRecorder()
        recorder.enable()
        recorder.add_handler(first_handler)
        recorder.add_handler(second_handler)
        recorder.record('foo', 'bar', source='source')

        first_handler.emit.assert_called_with('foo', 'bar', 'source')
        second_handler.emit.assert_called_with('foo', 'bar', 'source')

    def test_does_use_botocore_source_by_default(self):
        mock_handler = mock.Mock(spec=BaseHistoryHandler)
        recorder = HistoryRecorder()
        recorder.enable()
        recorder.add_handler(mock_handler)
        recorder.record('foo', 'bar')

        mock_handler.emit.assert_called_with('foo', 'bar', 'BOTOCORE')

    def test_does_not_call_handlers_when_never_enabled(self):
        mock_handler = mock.Mock(spec=BaseHistoryHandler)
        recorder = HistoryRecorder()
        recorder.add_handler(mock_handler)
        recorder.record('foo', 'bar')

        mock_handler.emit.assert_not_called()

    def test_does_not_call_handlers_when_disabled(self):
        mock_handler = mock.Mock(spec=BaseHistoryHandler)
        recorder = HistoryRecorder()
        recorder.enable()
        recorder.disable()
        recorder.add_handler(mock_handler)
        recorder.record('foo', 'bar')

        mock_handler.emit.assert_not_called()

    def test_can_ignore_handler_exceptions(self):
        mock_handler = mock.Mock(spec=BaseHistoryHandler)
        recorder = HistoryRecorder()
        recorder.enable()
        bad_handler = ExceptionThrowingHandler()
        recorder.add_handler(bad_handler)
        recorder.add_handler(mock_handler)
        try:
            recorder.record('foo', 'bar')
        except TerribleError:
            self.fail('Should not have raised a TerribleError')
        mock_handler.emit.assert_called_with('foo', 'bar', 'BOTOCORE')


class TestGetHistoryRecorder(unittest.TestCase):
    def test_can_get_history_recorder(self):
        recorder = get_global_history_recorder()
        self.assertTrue(isinstance(recorder, HistoryRecorder))

    def test_does_reuse_history_recorder(self):
        recorder_1 = get_global_history_recorder()
        recorder_2 = get_global_history_recorder()
        self.assertIs(recorder_1, recorder_2)
