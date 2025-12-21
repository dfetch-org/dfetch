import os

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.fileutil import copy_asset

logger = logging.getLogger(__name__)


def copy_asset_files(app, exc):
    asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_static")
    if exc is None:  # build succeeded
        for file in os.listdir(asset_dir):
            copy_asset(
                os.path.join(asset_dir, file), os.path.join(app.outdir, "_static")
            )


class Asciinema(nodes.General, nodes.Element):
    pass


def visit_html(self, node):
    rst_to_js_option_names: dict[str, str] = {
        "autoplay": "autoPlay",
        "idle-time-limit": "idleTimeLimit",
        "terminalfontsize": "terminalFontSize",
        "terminallineheight": "terminalLineHeight",
        "terminalfontfamily": "terminalFontFamily",
        "audiourl": "audioUrl",
    }

    options_raw = [
        "markers",
        "loop",
        "autoPlay",
        "preload",
        "pauseOnMarkers",
        "cols",
        "rows",
        "speed",
    ]

    for option, value in node["options"].items():
        node["options"][option] = ASCIINemaDirective.option_spec[option](value)

    gen = (
        (rst_option_name, js_option_name)
        for (rst_option_name, js_option_name) in rst_to_js_option_names.items()
        if rst_option_name in node["options"]
    )
    for rst_option_name, js_option_name in gen:
        node["options"][js_option_name] = node["options"].pop(rst_option_name)

    if node["type"] == "local":
        template = """<div id="asciicast-{id}"></div>
            <script>
                document.addEventListener("DOMContentLoaded", function() {{
                    AsciinemaPlayer.create(
                        "data:text/plain;base64,{src}",
                        document.getElementById('asciicast-{id}'),
                        {{{options} }});
                }});
            </script>"""
        option_template = '{}: "{}", '
        option_template_raw = "{}: {}, "
    else:
        template = """<script async id="asciicast-{src}" {options}
                src="https://asciinema.org/a/{src}.js"></script>"""
        option_template = 'data-{}="{}" '
        option_template_raw = 'data-{}="{}" '
    options = ""
    for n, v in node["options"].items():
        options += (
            option_template_raw.format(n, v)
            if n in options_raw
            else option_template.format(n, v)
        )
    tag = template.format(options=options, src=node["content"], id=node["id"])
    self.body.append(tag)


def visit_unsupported(self, node):
    logger.warning("asciinema: unsupported output format (node skipped)")
    raise nodes.SkipNode


def depart(self, node):
    pass


def bool_parse(argument):
    """Parse the option as boolean."""
    if argument is None:
        raise ValueError("Boolean option must have a value")

    val = str(argument).strip().lower()

    if val in ("true", "false"):
        return val
    raise ValueError("Must be boolean; True or False")


def bool_or_positive_int(argument):
    """Parse the option as boolean or positive integer."""
    try:
        return bool_parse(argument)
    except ValueError:
        return directives.positive_int(argument)


class ASCIINemaDirective(SphinxDirective):
    has_content = True
    final_argument_whitespace = False
    option_spec = {
        "cols": directives.positive_int,
        "rows": directives.positive_int,
        "autoplay": bool_parse,
        "preload": bool_parse,
        "loop": bool_or_positive_int,
        "start-at": directives.unchanged,
        "speed": directives.unchanged,
        "idle-time-limit": directives.unchanged,
        "theme": directives.unchanged,
        "poster": directives.unchanged,
        "fit": directives.unchanged,
        "controls": directives.unchanged,
        "markers": directives.unchanged,
        "pauseOnMarkers": bool_parse,
        "terminalfontsize": directives.unchanged,
        "terminalfontfamily": directives.unchanged,
        "terminallineheight": directives.unchanged,
        "path": directives.unchanged,
        "audiourl": directives.unchanged,
    }
    required_arguments = 1
    optional_arguments = len(option_spec)

    def run(self):
        arg = self.arguments[0]
        options = dict(self.env.config["sphinxcontrib_asciinema_defaults"])
        options.update(self.options)
        kw = {"options": options}
        path = options.get("path", "")
        if path and not path.endswith("/"):
            path += "/"
        fname = arg if arg.startswith("./") else path + arg
        if self.is_file(fname):
            kw["content"] = self.to_b64(fname)
            kw["type"] = "local"
            kw["id"] = fname
            logger.debug("asciinema: added cast file %s" % fname)
        else:
            kw["content"] = arg
            kw["id"] = arg
            kw["type"] = "remote"
            logger.debug("asciinema: added cast id %s" % arg)
        if "path" in kw["options"]:
            del kw["options"]["path"]
        return [Asciinema(**kw)]

    def is_file(self, rel_file):
        file_path = self.env.relfn2path(rel_file)[1]
        return os.path.isfile(file_path)

    def to_b64(self, filename):
        import base64

        file_path = self.env.relfn2path(filename)[1]
        with open(file_path, "rb") as file:
            content = file.read()
        b64encoded = base64.b64encode(content)
        return b64encoded.decode()


_NODE_VISITORS = {
    "html": (visit_html, depart),
    "latex": (visit_unsupported, None),
    "man": (visit_unsupported, None),
    "texinfo": (visit_unsupported, None),
    "text": (visit_unsupported, None),
}
