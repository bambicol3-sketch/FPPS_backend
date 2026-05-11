import os
from dataclasses import dataclass
from typing import Optional

from app.domains.template_rag.domain.value_object.form_type import FormType


@dataclass(frozen=True)
class FormTypeConfig:
    form_type: FormType
    folder_path: str
    sheet_name: str


class FormTypeMapping:
    def __init__(self) -> None:
        self._configs: dict[FormType, FormTypeConfig] = {}

    def register(
        self,
        form_type: FormType,
        folder_path: str,
        sheet_name: Optional[str] = None,
    ) -> None:
        self._configs[form_type] = FormTypeConfig(
            form_type=form_type,
            folder_path=folder_path,
            sheet_name=sheet_name or form_type.value,
        )

    def get(self, form_type: FormType) -> Optional[FormTypeConfig]:
        return self._configs.get(form_type)

    def items(self) -> list[FormTypeConfig]:
        return list(self._configs.values())


def default_mapping(base_dir: str) -> FormTypeMapping:
    mapping = FormTypeMapping()
    for form_type in FormType:
        mapping.register(
            form_type,
            folder_path=os.path.join(base_dir, form_type.value),
            sheet_name=form_type.value,
        )
    return mapping
