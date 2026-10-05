# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import uuid
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

_storage_client: Optional[storage.Client] = None


def get_storage_client() -> storage.Client:
    """Returns a singleton Storage client instance using ADC and GCP config."""
    global _storage_client
    if _storage_client is None:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if project_id and not project_id.isdigit():
            _storage_client = storage.Client(project=project_id)
        else:
            _storage_client = storage.Client()
    return _storage_client


def get_bucket_name() -> str:
    """Gets the ChefGemini media storage bucket name from configuration/environment."""
    bucket_name = os.environ.get("CHEFGEMINI_STORAGE_BUCKET") or os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT") or "chefgemini"
        bucket_name = f"chefgemini-media-{project_id}"
    return bucket_name


def check_media_bucket_exists() -> Dict[str, Any]:
    """Verifies that the ChefGemini GCS media bucket exists and is accessible.

    Returns:
        A dictionary with status and bucket details.
    """
    try:
        client = get_storage_client()
        bucket_name = get_bucket_name()
        bucket = client.bucket(bucket_name)
        exists = bucket.exists()
        return {
            "status": "success",
            "bucket_name": bucket_name,
            "exists": exists,
        }
    except Exception as e:
        return {
            "status": "error",
            "bucket_name": get_bucket_name(),
            "message": f"Failed to check bucket: {str(e)}",
            "exists": False,
        }


def upload_media_to_gcs(
    destination_blob_name: str,
    file_bytes: bytes,
    content_type: str = "image/png",
) -> Dict[str, Any]:
    """Uploads media (e.g. recipe images) to the ChefGemini Google Cloud Storage bucket and generates a public URL.

    Args:
        destination_blob_name: The destination filename or path in the bucket (e.g. 'recipes/spaghetti.png').
        file_bytes: Raw binary bytes of the file/image to upload.
        content_type: MIME type of the file (e.g. 'image/png', 'image/jpeg').

    Returns:
        A dictionary containing the public URL, GCS URI, and upload status.
    """
    try:
        client = get_storage_client()
        bucket_name = get_bucket_name()
        bucket = client.bucket(bucket_name)
        
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(file_bytes, content_type=content_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"
        gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"

        return {
            "status": "success",
            "bucket_name": bucket_name,
            "blob_name": destination_blob_name,
            "public_url": public_url,
            "gcs_uri": gcs_uri,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to upload media to GCS: {str(e)}",
        }
