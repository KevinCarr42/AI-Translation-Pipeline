import pytest
from unittest.mock import MagicMock
from scitrans.translate.document import _distribute_text_to_runs


def make_mock_run(text):
    run = MagicMock()
    run.text = text
    return run


class TestDistributeTextToRunsBug:

    def test_region_du_labrador_missing_space(self):
        """Row 4: 'Région du' loses its space at the run boundary."""
        translated = "MPO – Science, Région du Labrador de Newfoundland"
        runs = [make_mock_run("DFO – Science, "), make_mock_run("Newfoundland Labrador Region")]
        lengths = [15, 28]

        _distribute_text_to_runs(translated, runs, lengths)

        combined = runs[0].text + runs[1].text
        # The combined text must preserve the space between Région and du
        assert "Région du" in combined or "Région du" in runs[0].text or "Région du" in runs[1].text, \
            f"Missing space: got {repr(combined)}"
        assert combined.replace(" ", "") == translated.replace(" ", ""), \
            f"Characters lost or added: {repr(combined)} vs {repr(translated)}"

    def test_region_de_la_capitale_missing_space(self):
        """Row 6: 'Région de' loses its space at the run boundary."""
        translated = "MPO – SCAS, Région de la capitale nationale"
        runs = [make_mock_run("DFO – CSAS, "), make_mock_run("National Capital Region")]
        lengths = [12, 23]

        _distribute_text_to_runs(translated, runs, lengths)

        combined = runs[0].text + runs[1].text
        assert "Région de" in combined or "Région de" in runs[0].text or "Région de" in runs[1].text, \
            f"Missing space: got {repr(combined)}"

    def test_gestion_region_de_la_capitale_missing_space(self):
        """Row 7: longer first segment, same split-at-space bug."""
        translated = "MPO – Gestion des ressources, Région de la capitale nationale"
        runs = [make_mock_run("DFO –  Resource Management, "), make_mock_run("National Capital Region")]
        lengths = [28, 23]

        _distribute_text_to_runs(translated, runs, lengths)

        combined = runs[0].text + runs[1].text
        assert "Région de" in combined, f"Missing space: got {repr(combined)}"

    def test_no_space_lost_simple_two_runs(self):
        """Generic case: splitting 'hello world foo bar' across two runs must not lose spaces."""
        translated = "hello world foo bar"
        runs = [make_mock_run("hello wor"), make_mock_run("ld foo bar")]
        lengths = [9, 10]

        _distribute_text_to_runs(translated, runs, lengths)

        combined = runs[0].text + runs[1].text
        assert combined == translated, f"Expected {repr(translated)}, got {repr(combined)}"

    def test_three_runs_no_space_lost(self):
        """Three-run split must preserve all internal spaces."""
        translated = "alpha beta gamma delta epsilon"
        runs = [make_mock_run("aaaa"), make_mock_run("bbbb"), make_mock_run("cccccc")]
        lengths = [4, 4, 6]

        _distribute_text_to_runs(translated, runs, lengths)

        combined = runs[0].text + runs[1].text + runs[2].text
        assert combined == translated, f"Expected {repr(translated)}, got {repr(combined)}"

    def test_single_run_no_change(self):
        """Single run: no splitting needed, text should pass through unchanged."""
        translated = "some translated text"
        runs = [make_mock_run("original text here")]
        lengths = [18]

        _distribute_text_to_runs(translated, runs, lengths)

        assert runs[0].text == translated
