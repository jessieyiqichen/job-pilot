"""Tests for search command auto-append job_type keyword."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app

runner = CliRunner()


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.adapters.boss.BossAdapter.search")
def test_search_appends_intern_keyword(mock_search, mock_prefs, mock_db):
    """When job_type=实习 and query lacks intern keyword, auto-append 实习."""
    mock_prefs.return_value = {"job_type": "实习"}
    mock_search.return_value = []
    mock_db.return_value = MagicMock()

    result = runner.invoke(app, ["search", "AI产品经理", "--platform", "boss"])

    # The search adapter should receive query with 实习 appended
    mock_search.assert_called_once()
    actual_query = mock_search.call_args[0][0]
    assert "实习" in actual_query
    assert "自动追加关键词" in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.adapters.boss.BossAdapter.search")
def test_search_no_append_if_already_present(mock_search, mock_prefs, mock_db):
    """When query already contains job_type keyword, don't append."""
    mock_prefs.return_value = {"job_type": "实习"}
    mock_search.return_value = []
    mock_db.return_value = MagicMock()

    result = runner.invoke(app, ["search", "AI产品实习", "--platform", "boss"])

    mock_search.assert_called_once()
    actual_query = mock_search.call_args[0][0]
    # Should not double-append
    assert actual_query == "AI产品实习"
    assert "自动追加关键词" not in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.adapters.boss.BossAdapter.search")
def test_search_no_append_if_intern_in_english(mock_search, mock_prefs, mock_db):
    """When query contains 'intern', don't append 实习."""
    mock_prefs.return_value = {"job_type": "实习"}
    mock_search.return_value = []
    mock_db.return_value = MagicMock()

    result = runner.invoke(app, ["search", "AI product intern", "--platform", "boss"])

    mock_search.assert_called_once()
    actual_query = mock_search.call_args[0][0]
    assert actual_query == "AI product intern"
    assert "自动追加关键词" not in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.adapters.boss.BossAdapter.search")
def test_search_no_append_if_no_job_type(mock_search, mock_prefs, mock_db):
    """When no job_type preference, don't append anything."""
    mock_prefs.return_value = {}
    mock_search.return_value = []
    mock_db.return_value = MagicMock()

    result = runner.invoke(app, ["search", "AI产品经理", "--platform", "boss"])

    mock_search.assert_called_once()
    actual_query = mock_search.call_args[0][0]
    assert actual_query == "AI产品经理"
    assert "自动追加关键词" not in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.adapters.boss.BossAdapter.search")
def test_search_appends_fulltime_keyword(mock_search, mock_prefs, mock_db):
    """When job_type=全职 and query lacks it, append 全职."""
    mock_prefs.return_value = {"job_type": "全职"}
    mock_search.return_value = []
    mock_db.return_value = MagicMock()

    result = runner.invoke(app, ["search", "AI产品经理", "--platform", "boss"])

    mock_search.assert_called_once()
    actual_query = mock_search.call_args[0][0]
    assert "全职" in actual_query
