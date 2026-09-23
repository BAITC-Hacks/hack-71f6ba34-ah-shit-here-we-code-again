import unittest
from server import Catalog


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()
        self.catalog.ready = True
        self.catalog.index = [
            {'id': 1, 'article': '200300285_', 'name': 'Автомат Legrand'},
            {'id': 2, 'article': 'OTHER', 'name': 'Товар в наличии'},
        ]

    def test_exact_article_ignores_incidental_words(self):
        result = self.catalog.search('Расскажи о товаре 200300285_. Есть ли он в наличии?')
        self.assertEqual([p['id'] for p in result], [1])

    def test_exact_id_ignores_incidental_words(self):
        self.assertEqual([p['id'] for p in self.catalog.search('Товар 1 в наличии?')], [1])

    def test_ocr_trailing_underscore_can_be_restored_when_unique(self):
        self.assertEqual([p['id'] for p in self.catalog.search('200300285')], [1])

    def test_article_prefix_is_not_exact_match(self):
        self.assertEqual(self.catalog.search('20030028'), [])


if __name__ == '__main__':
    unittest.main()
