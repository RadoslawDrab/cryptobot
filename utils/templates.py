from pathlib import Path
from flask import render_template
from utils.api import ApiStatus

class Template:
    def __init__(self, path: Path | str, name: str, *keys: str):
        if not path.endswith('.html'):
            raise ValueError("Path doesn't contain html file")
        self.path = path
        self.name = name
        self.keys = keys

class TemplatesHandler:
    def __init__(self, *templates: Template, folder_path: Path | str = Path('.')):
        self._path: Path = Path(folder_path)
        self.templates = templates
    def render(self, name: str, **kwargs):
        templates = [template for template in self.templates if template.name == name]
        if len(templates) == 0:
            raise ApiStatus(500, f"Invalid template name '{name}'")
        template = templates[0]

        missing_keys = [key for key in template.keys if key not in kwargs.keys()]
        if len(missing_keys) > 0:
            raise ApiStatus(500, f"Keys are missing in rendering '{name}': {missing_keys}")


        path = Path.joinpath(self._path, template.path)
        return render_template(str(path), **kwargs)