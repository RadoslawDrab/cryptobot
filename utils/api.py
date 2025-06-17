import uuid
from typing import Self, Callable
from pathlib import Path
from flask import Flask
import importlib
import re

class ApiRule:
    CONVERTER_TYPES = (('string', 'str'), ('int', 'int'), ('float', 'float'), ('path', 'str'), ('uuid', 'uuid.UUID'))
    def __init__(self, path: str, converter_type: str | None = None):
        """
        :param path: Path name
        :param converter_type: Flask variable rule. See: https://flask.palletsprojects.com/en/stable/quickstart/#variable-rules
        """
        if converter_type is not None: ApiRule.check_type(converter_type)

        self.path = path
        self.type = converter_type.lower() if converter_type else None
    @staticmethod
    def check_type(converter_type: str, raise_error: bool = True):
        """
        Checks if converter type is valid
        :param converter_type: Flask converter type
        :param raise_error: Raise error if type is not valid
        """
        types = [t1 for t1, t2 in ApiRule.CONVERTER_TYPES]
        if converter_type.lower() not in types:
            if raise_error:
                raise ValueError(
                    f"Converter type '{converter_type.lower()}' is not valid type. Available values: {", ".join(types)}")
            else:
                return False
        return True
    @staticmethod
    def map_type(converter_type: str):
        """
        Gets valid python type from associated with converter type
        :param converter_type: Flask converter type
        """
        if not ApiRule.check_type(converter_type):
            raise ValueError(f"Invalid converter type: '{converter_type}'")

        return [py_type for conv_type, py_type in ApiRule.CONVERTER_TYPES if conv_type == converter_type][0]

class ApiEndpoint:
    """
    Create API endpoint.\n
    Use ``create_tree`` if you want to use file-based api paths.
    It'll automatically create folders and files with valid functions in ``api`` folder in current working directory.\n
    If you want to add new endpoint just create new ``ApiEndpoint`` valid variable.
    """
    METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTION')
    ERROR_CODES = [
        (200, 'Ok'),
        (201, 'Created'),
        (202, 'Accepted'),
        (301, 'Moved Permanently'),
        (302, 'Found'),
        (304, 'Not Modified'),
        (307, 'Temporary Redirect'),
        (308, 'Permanent Redirect'),
        (400, 'Bad Request'),
        (401, 'Unauthorized'),
        (403, 'Forbidden'),
        (404, 'Not Found'),
        (405, 'Method Not Allowed'),
        (500, 'Internal Server Error'),
        (501, 'Not Implemented'),
        (502, 'Bad Gateway'),
        (503, 'Service Unavailable')
    ]
    def __init__(self, keys: list[str | ApiRule], children: list[Self] | None = None , methods: list[str] | None = None, callback: Callable[[dict], str | dict] | None = None, app: Flask | None = None):
        if methods is not None:
            for method in methods:
                ApiEndpoint.valid_method(method)
        self.callback = callback
        self.methods = [method.upper() for method in methods] if methods else ['GET']
        self._keys = keys
        # Formats keys for Flask usage
        self._formatted_keys = [
            f'<{key.type + ':' if key.type is not None else ''}{key.path}>'
            if isinstance(key, ApiRule) else
            key
            for key in keys
            if key != '/'
        ]
        self._app = app
        self._endpoints: list[str] = []
        self.children: list[Self] = children or []

    @property
    def path(self):
        """Gets joint path"""
        return '/' + "/".join(self._formatted_keys)
    @property
    def callback_name(self):
        return 'init'
    @callback_name.setter
    def callback_name(self, name: str):
        self.callback_name = name.lower()

    def route_exists(self, path: str):
        """
        Checks if specific route exists in API
        :param path: path to check
        :return: bool
        """
        for rule in self._app.url_map.iter_rules():
            if rule.rule == path:
                return True
        return False
    def set_app(self, app: Flask | None):
        self._app = app
        return self
    def create_tree(self):
        """
        Creates tree API in ``api`` folder.\n
        For each endpoint creates folder with path name and ``__init__.py`` file with function name specified in ``callback_name`` with params if API endpoint has any params
        """
        endpoints = self.create_endpoints()

        # API folder path
        main_folder = Path.joinpath(Path.cwd(), 'api')

        # Creates folder if it doesn't exist
        Path.mkdir(main_folder, exist_ok=True)

        # File content for __init__.py
        file_content = [
            "from flask import request",
            "{IMPORTS}"
            "# PATH: {PATH}",
            '# METHODS: {METHODS}',
            "def init({PARAMS}):",
            "   return"
        ]

        all_endpoints: list[dict] = []

        def make_view_func(f):
            return lambda **kwargs: {**ApiEndpoint.get_status(200), **(f(**kwargs) or ApiEndpoint.get_status(501))} if f else ApiEndpoint.get_error(501)
        def endpoint(main_path: str, data: dict, paths: list[str], queries: list[ApiRule]):
            """
            Creates recursive endpoint for each path
            :param main_path: Starting path
            :param data: Path data. Includes keys: ``path`` (current path), ``children`` (direct children), ``methods`` (available methods), ``query`` (any query parameters), ``callback`` (callback for this route)
            :param paths: Current parent paths
            :param queries: Current query parameters
            :return: None
            """
            data_path = data.get('path')
            children = data.get('children') or []
            methods = data.get('methods') or []
            query: list[ApiRule] = data.get('query') or []

            current_paths = [re.sub(r'^/+', '', p) for p in [*paths, data_path] if p and p != '/']
            current_path = "/" + "/".join(current_paths)

            # Name for current path
            name = '' if data_path == '/' else ApiEndpoint.format_path(data_path).lower()
            folder_path = Path.joinpath(main_folder, main_path, name)
            file_path = Path.joinpath(folder_path, '__init__.py')

            # Creates folder if it doesn't exist
            Path.mkdir(Path.joinpath(folder_path), exist_ok=True)

            if not Path.exists(file_path):
                with open(file_path, 'w') as f:
                    # Maps each query parameter with valid python type
                    func_params = [f'{q.path}: {ApiRule.map_type(q.type)}' for q in [*query, *queries]]
                    func_params.append('**kwargs')
                    uuid_present = any(q.type == 'uuid' for q in query)
                    f.write("\n".join(file_content).format(
                        PATH=data_path,
                        METHODS=" | ".join(methods),
                        PARAMS=", ".join(func_params),
                        IMPORTS="" if not uuid_present else "import uuid"
                    ))
            # Adds url rule if app is present and actual route doesn't exist already
            if self._app and not self.route_exists(data_path):
                # Path relative to current working directory separated by dot. Path for python import path
                relative_path = ".".join(folder_path.relative_to(Path.cwd()).as_posix().split('/'))
                # Specific python module
                module = importlib.import_module(str(relative_path))

                func = getattr(module, self.callback_name, None)
                # Checks if module contains init function
                # if hasattr(module, self.callback_name):
                all_endpoints.append({
                    'rule': current_path,
                    'endpoint': f"{current_path}_{id(data)}",
                    'view_func': make_view_func(func),
                    'methods': methods
                })

            for child in children:
                # Creates endpoint for direct children
                endpoint(str(Path.joinpath(Path(main_path), './' + name)), child, current_paths, [*queries, *query])

        endpoint(str(Path('./')), endpoints, ['/'], [])

        if self._app:
            all_endpoints.sort(key=lambda d: d.get('rule'), reverse=True)
            for endpoint in all_endpoints:
                # Adds Flask url rule for path
                self._app.add_url_rule(**endpoint)
    def create_endpoints(self):
        """Creates url endpoints for API"""

        def create_children_endpoints(endpoint: Self):
            # Path to endpoint
            path = endpoint._create_endpoint()
            # All endpoint info
            endpoint_info = {
                'path': path,
                'methods': endpoint.methods,
                'callback': endpoint.callback,
                'query': [key for key in endpoint._keys if isinstance(key, ApiRule)],
                'children': []
            }

            for child in endpoint.children:
                # Updates child app for current app
                child.set_app(self._app)
                # Gets child endpoint data
                child_data = create_children_endpoints(child)
                endpoint_info['children'].append(child_data)

            return endpoint_info

        return create_children_endpoints(self)
    def _create_endpoint(self):
        if self._app is None:
            raise RuntimeError('Flask app not found')

        if self.callback:
            self._app.add_url_rule(
                self.path,
                endpoint=f"{self.path}_{id(self)}",
                view_func=lambda **kwargs: self.callback(kwargs),
                methods=self.methods
            )
        return self.path

    @staticmethod
    def get_status(code: int, message: str | None = None):
        return {'status': {'code': code, 'message': message if message else [m for c, m in ApiEndpoint.ERROR_CODES if c == code][0]}}
    @staticmethod
    def get_error(code: int, message: str | None = None):
        return ApiEndpoint.get_status(code, message), code
    @staticmethod
    def format_path(path: str):
        """
        Formats Flask path to OS path
        :param path: Flask path
        :return: OS valid path
        """
        patterns: list[tuple[str, str]] = [
            (r'<', '['),
            (r'>', ']'),
            (r':', '-'),
            (r' ', '_'),
            (r'^/', ''),
        ]
        def replace(p: str):
            if len(patterns) == 0:
                return p
            pattern, repl = patterns[0]
            patterns.pop(0)
            return replace(re.sub(pattern, repl, p))
        return replace(path)
    @staticmethod
    def valid_method(method: str, raise_error: bool = True):
        if method.upper() not in ApiEndpoint.METHODS:
            if raise_error:
                raise ValueError(f"Invalid route method '{method}'")
            else:
                return False
        return True