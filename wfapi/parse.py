import json
import re

__all__ = ["get_globals_from_home"]


def get_globals_from_home(content):
    for source in SCRIPT_TAG_REGEX.findall(content):
        if "(" in source:
            # function call found while parsing.
            continue

        for key, value in SCRIPT_VAR_REGEX.findall(source):
            if value.startswith("'") and value.endswith("'"):
                assert '"' not in value
                value = '"{}"'.format(value[+1:-1])

            if key == "FIRST_LOAD_FLAGS" or key == "SETTINGS":
                # TODO: non-standard json parse by demjson?
                continue

            value = json.loads(value)
            yield key, value


SCRIPT_TAG_REGEX = re.compile("".join([
    re.escape('<script type="text/javascript">'), "(.*?)", re.escape('</script>'),
]), re.DOTALL)
SCRIPT_VAR_REGEX = re.compile("".join([
    re.escape("var "), "(.*?)", re.escape(" = "), "(.*?|\{.*?\})", re.escape(";"), '$',
]), re.DOTALL | re.MULTILINE)
