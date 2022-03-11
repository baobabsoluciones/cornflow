from typing import Any, Dict
import pickle
from uuid import uuid4

from airflow.models.xcom import BaseXCom
from airflow.providers.google.cloud.hooks.gcs import GCSHook


class GCSXComBackend(BaseXCom):
    PREFIX = "xcom_gcs://"
    BUCKET_NAME = "cornflow"

    @staticmethod
    def serialize_value(value: Any):
        if isinstance(value, Dict):
            hook = GCSHook()
            object_name = f"model/data_{uuid4()}.pickle"

            with hook.provide_file_and_upload(
                bucket_name=GCSXComBackend.BUCKET_NAME, object_name=object_name
            ) as f:
                print(f"F: {f}")
                print(f"DICT: {f.__dict__}")
                print(f"TYPE: {type(f)}")
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
                print(f"F: {f}")
                print(f"DICT: {f.__dict__}")
                print(f"NAME: {f.name}")
                print(f"File: {f.file}")
                f.flush()
                print(f"F: {f}")
                print(f"DICT: {f.__dict__}")
                print(f"NAME: {f.name}")
                print(f"File: {f.file}")

                result = pickle.load(f)

        return result
