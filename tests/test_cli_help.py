import importlib
import sys

import pytest

CLI_MODULES = [
    "scripts.retrieve",
    "scripts.combine",
    "scripts.create_samples",
    "db.scripts.ingest",
    "db.scripts.db_connect",
    "db.scripts.trim",
    "db.scripts.export_titles",
    "db.scripts.export_tech_names",
    "db.scripts.export_context",
    "db.scripts.export_comments_for_techs",
    "db.scripts.export_stories_meta",
    "analytics.embeddings.scripts.classify_tech",
    "analytics.embeddings.scripts.build_rel_matrix",
    "analytics.embeddings.scripts.lemmatize_file",
    "analytics.embeddings.scripts.sentences_to_vectors",
    "analytics.embeddings.scripts.train_model",
    "analytics.embeddings.scripts.calculate_irr",
    "analytics.embeddings.scripts.calculate_sentiment",
    "analytics.embeddings.scripts.precompute",
    "visualization.draw_relationship_map",
    "visualization.draw_wordcloud",
    "visualization.draw_irr_plot",
    "visualization.draw_sentiment_plot",
]


@pytest.mark.parametrize("module_name", CLI_MODULES)
def test_help_works(module_name, monkeypatch, capsys):
    # Регрессия: "%" в тексте help ломал --help у calculate_sentiment
    module = importlib.import_module(module_name)
    monkeypatch.setattr(sys, "argv", [module_name, "--help"])
    with pytest.raises(SystemExit) as exc:
        module.parse_args()
    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out
