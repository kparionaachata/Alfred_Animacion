import unittest
from pathlib import Path
from unittest.mock import patch

import estudio_musical as app


class PreferenceTests(unittest.TestCase):
    def test_engine_active_before_lazy_model_load(self):
        with patch.object(app, "_request_json", return_value={"object": "list", "data": []}):
            self.assertIn("Servicio activo", app.estado_motor())

    def test_engine_ready_with_openai_style_model_list(self):
        response = {"object": "list", "data": [{"id": "acestep/turbo", "name": "ACE-Step turbo"}]}
        with patch.object(app, "_request_json", return_value=response):
            self.assertEqual("Motor listo: ACE-Step turbo", app.estado_motor())

    def test_default_suggestion_without_ratings(self):
        with patch.object(app, "PREFERENCES", Path("missing-ratings.jsonl")):
            prompt, fidelity, message = app.sugerencia_aprendida()
        self.assertIn("instrumental", prompt)
        self.assertEqual(0.70, fidelity)
        self.assertIn("Aun no", message)

    def test_weighted_positive_ratings(self):
        rows = [
            {"rating": 5, "fidelity": 0.8, "description": "orquesta suave"},
            {"rating": 4, "fidelity": 0.6, "description": "orquesta suave"},
            {"rating": 2, "fidelity": 0.2, "description": "ignorada"},
        ]
        with patch.object(app, "_ratings", return_value=rows):
            prompt, fidelity, message = app.sugerencia_aprendida()
        self.assertEqual("orquesta suave", prompt)
        self.assertEqual(0.71, fidelity)
        self.assertIn("2 calificacion", message)


if __name__ == "__main__":
    unittest.main()
