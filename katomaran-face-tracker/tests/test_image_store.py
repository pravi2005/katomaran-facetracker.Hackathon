from datetime import datetime

import numpy as np
import pytest

from app.errors import ImageStorageError
from app.storage.image_store import ImageStore, crop_with_padding, format_face_id

WHEN = datetime(2026, 10, 3, 10, 30, 15, 120000).astimezone()


def img():
    return np.random.default_rng(0).integers(0, 255, size=(60, 60, 3), dtype=np.uint8)


def test_directory_layout_and_relative_paths(tmp_path):
    store = ImageStore(tmp_path)
    reg = store.save_registration("F001", img(), WHEN)
    ent = store.save_entry("F001", img(), WHEN)
    ext = store.save_exit("F001", img(), WHEN)
    day = WHEN.strftime("%Y-%m-%d")
    assert reg == f"registrations/{day}/F001.jpg"
    assert ent.startswith(f"entries/{day}/F001_") and ent.endswith(".jpg")
    assert ext.startswith(f"exits/{day}/F001_")
    assert all((tmp_path / p).is_file() for p in (reg, ent, ext))
    assert not list(tmp_path.rglob("*.tmp"))          # atomic write leaves no temp files


def test_same_millisecond_does_not_overwrite(tmp_path):
    store = ImageStore(tmp_path)
    first, second = store.save_entry("F001", img(), WHEN), store.save_entry("F001", img(), WHEN)
    assert first != second


@pytest.mark.parametrize("bad", ["../evil", "F1", "f001", "F001/../x", "", "F001.jpg"])
def test_unsafe_face_ids_rejected(tmp_path, bad):
    with pytest.raises(ImageStorageError):
        ImageStore(tmp_path).save_entry(bad, img(), WHEN)


def test_empty_image_rejected(tmp_path):
    with pytest.raises(ImageStorageError):
        ImageStore(tmp_path).save_entry("F001", np.zeros((0, 0, 3), np.uint8), WHEN)


def test_crop_with_padding_clamps_to_frame():
    image = np.zeros((100, 100, 3), np.uint8)
    crop = crop_with_padding(image, (80, 80, 120, 120), 0.5)
    assert crop.shape[0] <= 100 and crop.shape[1] <= 100
    assert crop_with_padding(image, (50, 50, 50, 50)) is None


def test_face_id_format():
    assert format_face_id(1) == "F001" and format_face_id(12) == "F012" and format_face_id(1234) == "F1234"
