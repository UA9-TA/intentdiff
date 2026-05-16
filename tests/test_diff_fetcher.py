from unittest.mock import patch

from intentdiff.diff_fetcher import fetch_diff


@patch("subprocess.run")
def test_fetch_diff_head(mock_run):
    mock_run.return_value.stdout = "dummy diff content"
    result = fetch_diff()

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "git" in args
    assert "diff" in args
    assert "HEAD" in args
    assert result == "dummy diff content"


@patch("subprocess.run")
def test_fetch_diff_staged(mock_run):
    mock_run.return_value.stdout = "dummy staged diff"
    fetch_diff(staged=True)

    args = mock_run.call_args[0][0]
    assert "--cached" in args


@patch("subprocess.run")
def test_fetch_diff_commit(mock_run):
    mock_run.return_value.stdout = "dummy commit diff"
    fetch_diff(commit="abc1234")

    args = mock_run.call_args[0][0]
    assert "show" in args
    assert "abc1234" in args
