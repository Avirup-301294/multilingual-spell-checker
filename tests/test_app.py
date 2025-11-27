import unittest
import json
from app import app

class SpellCheckerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Spell Checker Pro', response.data)

    def test_check_spelling(self):
        payload = {'text': 'teh world', 'mode': 'balanced'}
        response = self.app.post('/check', data=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check tokens structure
        self.assertIn('tokens', data)
        tokens = data['tokens']
        self.assertTrue(len(tokens) > 0)
        
        # Find "teh" token
        teh_token = next((t for t in tokens if t['text'] == 'teh'), None)
        self.assertIsNotNone(teh_token)
        self.assertFalse(teh_token['is_valid'])
        self.assertTrue(len(teh_token['suggestions']) > 0)
        self.assertEqual(teh_token['suggestions'][0]['word'], 'the')

    def test_check_spelling_json(self):
        payload = {'text': 'teh world', 'mode': 'balanced'}
        response = self.app.post('/check', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('tokens', data)

    def test_empty_text(self):
        payload = {'text': ''}
        response = self.app.post('/check', data=payload)
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
