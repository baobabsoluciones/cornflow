from typing import Any, Dict
import pickle
from uuid import uuid4
from datetime import datetime

from airflow.models.xcom import BaseXCom
from airflow.providers.google.cloud.hooks.gcs import GCSHook


class GCSXComBackend(BaseXCom):
    PREFIX = "xcom_gcs://"
    BUCKET_NAME = "cornflow"

    @staticmethod
    def serialize_value(value: Any):
        if isinstance(value, Dict):
            hook = GCSHook()
            if "model_name" in value.keys():
                object_name = f"model/{value['model_name']}/data_{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}.pickle"
            else:
                object_name = f"model/data_{uuid4()}.pickle"
            value["location"] = object_name

            with hook.provide_file_and_upload(
                bucket_name=GCSXComBackend.BUCKET_NAME, object_name=object_name
            ) as f:
                pickle.dump(value, f)

            value = f"{GCSXComBackend.PREFIX}{object_name}"

        return BaseXCom.serialize_value(value)

    @staticmethod
    def deserialize_value(result) -> Any:
        result = BaseXCom.deserialize_value(result)
        if isinstance(result, str) and result.startswith(GCSXComBackend.PREFIX):
            object_name = result.replace(GCSXComBackend.PREFIX, "")
            hook = GCSHook()

            with hook.provide_file(
                bucket_name=GCSXComBackend.BUCKET_NAME, object_name=object_name
            ) as f:
                f.flush()
                result = pickle.load(f)

        return result
