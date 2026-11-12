from skelion_agent.worker import _extract_pr_url


def test_extract_pr_url_returns_real_url():
    assert _extract_pr_url("created https://github.com/acme/app/pull/42") == (
        "created https://github.com/acme/app/pull/42"
    )


def test_extract_pr_url_does_not_fabricate_success():
    assert _extract_pr_url("agent completed without publishing a pull request") is None
