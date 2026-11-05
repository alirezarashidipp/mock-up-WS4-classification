from app.models import COLUMNS, InputField


def prepare_fields(row: dict[str, str], columns=COLUMNS) -> list[dict[str, str]]:
    id_column = columns["input"]["id"]
    definitions = columns["definitions"]
    excluded = columns["exclude"]
    names = []
    for name in columns["input_order"]:
        if name in row and name != id_column and name not in excluded:
            names.append(name)
    # Keep additional source columns in their original order.
    for name in row:
        if name != id_column and name not in excluded and name not in names:
            names.append(name)

    fields = []
    for name in names:
        field = InputField(name=name, description=definitions[name], value=row[name])
        fields.append(field.model_dump())
    return fields
