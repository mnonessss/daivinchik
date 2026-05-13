from models import ProfilePhotos
from profiles.schema import ProfilePhotoResponse
from storage.s3_storage import is_s3_enabled, presigned_get_url


def profile_photo_to_response(photo: ProfilePhotos) -> ProfilePhotoResponse:
    url = None
    if photo.s3_object_key and is_s3_enabled():
        url = presigned_get_url(photo.s3_object_key)
    return ProfilePhotoResponse(
        id=photo.id,
        profile_id=photo.profile_id,
        telegram_file_id=photo.telegram_file_id,
        s3_object_key=photo.s3_object_key,
        url=url,
    )
