"""Tests für Feedback-Logging + Silent Patch."""

from __future__ import annotations

from datetime import date

import frontmatter

from nextstep_os.core.feedback import (
    build_feedback,
    list_feedback,
    record,
    silent_patch_skill,
    write_feedback,
)
from nextstep_os.core.models import FeedbackStatus, FeedbackTyp


def test_silent_patch_adds_learning_section(tmp_path):
    skill_path = tmp_path / "skill.md"
    skill_path.write_text(
        "---\nid: t\nname: Test\n---\n\n## SOP\nDo stuff.\n", encoding="utf-8"
    )
    silent_patch_skill(skill_path, "Immer zuerst fragen.", heute=date(2026, 4, 14))
    post = frontmatter.load(skill_path)
    assert "📝 Learnings" in post.content
    assert "2026-04-14" in post.content
    assert "Immer zuerst fragen" in post.content


def test_silent_patch_appends_to_existing_section(tmp_path):
    skill_path = tmp_path / "skill.md"
    skill_path.write_text(
        "---\nid: t\nname: Test\n---\n\n## SOP\n...\n\n## 📝 Learnings\n\n- **2026-01-01:** Alt.\n",
        encoding="utf-8",
    )
    silent_patch_skill(skill_path, "Neu.", heute=date(2026, 4, 14))
    post = frontmatter.load(skill_path)
    assert "Alt." in post.content
    assert "Neu." in post.content
    assert post.content.count("## 📝 Learnings") == 1


def test_build_feedback_uses_slug_id():
    entry = build_feedback(titel="Meine Test-Idee!", typ=FeedbackTyp.VERBESSERUNGS_IDEE)
    assert "meine-test-idee" in entry.id
    assert entry.status == FeedbackStatus.NEU


def test_write_and_list_feedback(isolated_config):
    entry = build_feedback(titel="Erster Eintrag", typ=FeedbackTyp.ERFOLG, learning="Klappt.")
    path = write_feedback(isolated_config, entry)
    assert path.exists()
    entries = list_feedback(isolated_config)
    assert len(entries) == 1
    assert entries[0].titel == "Erster Eintrag"


def test_record_with_patch_skill(isolated_config, tmp_path):
    skill_path = isolated_config.paths.skills_dir / "demo.md"
    skill_path.write_text(
        "---\nid: demo\nname: Demo\n---\n\n## SOP\n...\n", encoding="utf-8"
    )
    entry = record(
        isolated_config,
        titel="Verbesserung",
        typ=FeedbackTyp.VERBESSERUNGS_IDEE,
        learning="Immer mit Smalltalk einsteigen.",
        skill_id="demo",
        skill_path=skill_path,
        patch_skill=True,
    )
    assert entry.path is not None and entry.path.exists()
    body = skill_path.read_text(encoding="utf-8")
    assert "📝 Learnings" in body
    assert "Smalltalk" in body
