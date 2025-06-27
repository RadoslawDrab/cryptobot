from typing import Self, Callable
from pathlib import Path
from flask import Flask, Request
import importlib
import re
import json

class ApiStatus(Exception):
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
    def __init__(self, code: int, message: str | None = None):
        self.code = code
        self.message = message
    @property
    def status(self):
        return ApiStatus.get_status(self.code, self.message)

    @staticmethod
    def get_status(code: int, message: str | None = None):
        return {
            'status': {
                'code': code,
                'message': message if message else [m for c, m in ApiStatus.ERROR_CODES if c == code][0]
            }
        }
    @staticmethod
    def get_flask_error(code: int, message: str | None = None):
        return ApiStatus.get_status(code, message), code
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
    def tree(self):
        def get_path(endpoint: dict):
            path = endpoint.get('path')
            children = endpoint.get('children')
            info  = {
                'path': re.sub('<', '[', re.sub('>', ']', path)),
                'methods': endpoint.get('methods'),
                'children': []
            }
            for child in children:
                info['children'].append(get_path(child))
            return info
        return get_path(self.create_endpoints())

    @property
    def html_tree(self):
        """
        HTML presenting tree view of an API
        """
        return f"""
            <div style="display: block; max-width: 600px; margin: 0 auto;">
                <h1>Tree View</h1>
                <hr />
                <pre>{json.dumps(self.tree, indent=2)}</pre>
            </div>
            """
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
    def create_tree(self, **endpoint_kwargs: tuple[str, str | None, any]):
        """
        Creates tree API in ``api`` folder.
        For each endpoint creates folder with path name and ``__init__.py`` file with function name specified in ``callback_name`` with params if API endpoint has any params
        :param endpoint_kwargs: Keyword arguments to pass to endpoint. ``dict[PARAM_NAME,tuple[TYPE,IMPORT_PATH,VALUE]]``
        """
        endpoints = self.create_endpoints()

        # API folder path
        main_folder = Path.joinpath(Path.cwd(), 'api')

        # Creates folder if it doesn't exist
        Path.mkdir(main_folder, exist_ok=True)

        # File content for __init__.py
        file_content = [
            "from flask import request",
            "{IMPORTS}",
            "",
            "# PATH: {PATH}",
            '# METHODS: {METHODS}',
            "def init({PARAMS}):",
            "   return"
        ]

        def get_endpoint_kwargs(info: dict) -> dict[str, tuple[str, str | None, any]]:
            return {
                'api': ('ApiEndpoint', 'utils.api', self),
                'path': ('str', None, info.get('path'))
            }

        all_endpoints: list[dict] = []

        def make_view_func(f, info: dict[str, tuple[str, str | None, any]]):
            def func(**kwargs):
                if not f:
                    # Not implemented
                    return ApiStatus.get_flask_error(501)
                try:
                    data = f(**kwargs, **{key: value for key, (_, _, value) in info.items()})
                    if isinstance(data, ApiStatus):
                        return data.status
                    if type(data) == tuple and type(data[1]) == int:
                        return { **ApiStatus.get_status(data[1]), **data[0] }
                    if type(data) == dict:
                        return {
                            **ApiStatus.get_status(200),
                            'data': data
                        }
                    # HTML
                    elif type(data) == str:
                        return data
                    # Not implemented
                    else:
                        return ApiStatus.get_flask_error(501)
                # Some error
                except TypeError as e:
                    return ApiStatus.get_flask_error(500, str(e))
            return func
        def endpoint(main_path: str, data: dict, paths: list[str], queries: list[ApiRule], kwargs: dict[str, tuple[str, str | None, any]] | None = None):
            """
            Creates recursive endpoint for each path
            :param main_path: Starting path
            :param data: Path data. Includes keys: ``path`` (current path), ``children`` (direct children), ``methods`` (available methods), ``query`` (any query parameters), ``callback`` (callback for this route)
            :param paths: Current parent paths
            :param queries: Current query parameters
            :param kwargs: Keyword arguments to pass to endpoint. ``dict[PARAM_NAME,tuple[TYPE,IMPORT_PATH,VALUE]]``
            :return: None
            """
            data_path = data.get('path')
            children = data.get('children') or []
            methods = data.get('methods') or []
            query: list[ApiRule] = data.get('query') or []
            endpoint_info = {
                'path': data_path,
                'methods': methods
            }
            kwargs = {**get_endpoint_kwargs(endpoint_info), **kwargs}

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
                    func_params.extend([f'{key}: {value_type}' for key, (value_type, import_path, *_) in kwargs.items()])
                    func_params.append('**kwargs')
                    uuid_present = any(q.type == 'uuid' for q in query)

                    f.write("\n".join(file_content).format(
                        PATH=data_path,
                        METHODS=" | ".join(methods),
                        PARAMS=", ".join(func_params),
                        IMPORTS="\n".join([
                            "" if not uuid_present else "import uuid",
                            *[f'from {import_path} import {value_type}' for value_type, import_path, *_ in kwargs.values() if import_path is not None]
                        ])
                    ))
            else:
                with open(file_path, 'r') as f:
                    content = f.readlines()
                    new_content = []
                    for line in content:
                        if line.startswith('# PATH: '):
                            line = f'# PATH: {data_path}\n'
                        if line.startswith('# METHODS: '):
                            line = f'# METHODS: {" | ".join(methods)}\n'


                        new_content.append(line)
                    with open(file_path, 'w') as f:
                        f.write("".join(new_content))

            # Adds url rule if app is present and actual route doesn't exist already
            if self._app and not self.route_exists(data_path):
                # Path relative to current working directory separated by dot. Path for python import path
                relative_path = ".".join(folder_path.relative_to(Path.cwd()).as_posix().split('/'))
                # Specific python module
                module = importlib.import_module(str(relative_path))

                func = getattr(module, self.callback_name, None)
                all_endpoints.append({
                    'rule': '/api/' + current_path,
                    'endpoint': f"{current_path}_{id(data)}",
                    'view_func': make_view_func(func, kwargs),
                    'methods': methods
                })

            for child in children:
                # Creates endpoint for direct children
                endpoint(str(Path.joinpath(Path(main_path), './' + name)), child, current_paths, [*queries, *query], kwargs)

        endpoint(str(Path('./')), endpoints, ['/'], [], endpoint_kwargs)

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

        if self.callback and not self.route_exists(self.path):
            self._app.add_url_rule(
                '/api/' + self.path,
                endpoint=f"{self.path}_{id(self)}",
                view_func=lambda **kwargs: self.callback(kwargs),
                methods=self.methods
            )
        return self.path

    @staticmethod
    def get_body(request: Request, *keys: str):
        if not request.is_json:
            raise ApiStatus(400, 'Invalid body type')
        data: dict = request.get_json(True)
        ApiEndpoint.check_body(data, *keys)
        return data
    @staticmethod
    def check_body(body: dict, *keys: str):
        missing_keys = [key for key in keys if body.get(key) is None]
        if len(missing_keys) > 0:
            raise ApiStatus(400, f"Body is missing keys: {missing_keys}")

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