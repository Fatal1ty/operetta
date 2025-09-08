import logging

from mashumaro import MissingField
from mashumaro.exceptions import InvalidFieldValue

log = logging.getLogger(__name__)


def collect_exception_chain_metadata(exc):
    metadata = []
    e = exc
    last_value = None
    last_suggestion = None
    while e:
        if isinstance(e, InvalidFieldValue):
            entry = {
                "object_type": e.holder_class_name,
                "field": e.field_name,
                "expected_type": e.field_type_name,
                "issue": "Invalid value provided",
            }
            last_value = e.field_value
            last_suggestion = (
                f"Provide a valid value that matches "
                f"the required format and type"
            )
            metadata.append(entry)
            e = e.__cause__ or e.__context__
        elif isinstance(e, MissingField):
            entry = {
                "object_type": e.holder_class_name,
                "field": e.field_name,
                "expected_type": e.field_type_name,
                "issue": f"Missing required field '{e.field_name}'",
            }
            last_suggestion = f"Provide the required '{e.field_name}' field"
            metadata.append(entry)
            break
        else:
            break
    metadata[-1]["incoming_value"] = last_value
    metadata[-1]["suggestion"] = last_suggestion
    return metadata
