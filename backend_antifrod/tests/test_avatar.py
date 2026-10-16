import unittest
from io import BytesIO

from fastapi import HTTPException
from PIL import Image

from services.avatar_service import MAX_UPLOAD_BYTES, normalize_image


class AvatarTest(unittest.TestCase):
    def test_normalizes_and_resizes_transparent_image(self):
        source = BytesIO()
        Image.new('RGBA', (1024, 768), (255, 0, 0, 0)).save(source, 'PNG')
        with Image.open(BytesIO(normalize_image(source.getvalue()))) as result:
            self.assertEqual(result.format, 'JPEG')
            self.assertEqual(result.size, (512, 384))
            self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_rejects_invalid_and_oversized_files(self):
        for data, status in [(b'<svg></svg>', 415), (b'x' * (MAX_UPLOAD_BYTES + 1), 413), (b'', 415)]:
            with self.assertRaises(HTTPException) as error:
                normalize_image(data)
            self.assertEqual(error.exception.status_code, status)

    def test_rejects_truncated_image(self):
        source = BytesIO()
        Image.new('RGB', (100, 100)).save(source, 'JPEG')
        with self.assertRaises(HTTPException):
            normalize_image(source.getvalue()[:100])
