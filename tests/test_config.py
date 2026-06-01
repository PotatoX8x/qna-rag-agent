from app.core import config


def test_expand_uses_env_when_set(monkeypatch):
    monkeypatch.setenv("SAMPLE_VAR", "from-env")
    assert config._expand("x: ${SAMPLE_VAR:-fallback}") == "x: from-env"


def test_expand_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("SAMPLE_VAR", raising=False)
    assert config._expand("x: ${SAMPLE_VAR:-fallback}") == "x: fallback"


def test_expand_leaves_bare_placeholder_literal(monkeypatch):
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    assert config._expand("x: ${MISSING_SECRET}") == "x: ${MISSING_SECRET}"


def test_load_config_returns_expected_tree():
    cfg = config.load_config()
    assert cfg["mlflow"]["experiment"] == "qna"
    assert "data_dir" in cfg["database"]
