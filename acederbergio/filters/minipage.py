import json

import panflute as pf

from acederbergio.filters import util


class FilterMinipage(util.BaseFilter):
    """Turn fenced divs into minipages.

    This is because ``layout`` does not fit my purposes. I would like something
    like:

    ```
    ::: {
        .minipage minipage_width=.50
        minipage_align=top
        minipage_height=1
    }
    :::
    ```
    """

    filter_name = "minipage"

    def hydrate_minipage(self, el: pf.Element):

        env_start = "\\begin{minipage}"
        env_stop = "\\end{minipage}%\n%\n"

        if (align := el.attributes.get("minipage-align", "t")) not in "tbc":
            raise ValueError

        env_start += f"[{align}]"

        height_raw = el.attributes.get("minipage-height", "unset")
        if height_raw != "unset":
            height = float(height_raw)
            if not (0 <= height <= 1):
                raise ValueError

            env_start += rf"[{height}\textheight]" if height < 1 else r"[\textheight]"

        width = float(el.attributes.get("minipage-width", "0.49"))
        if not (0 <= width <= 1):
            raise ValueError

        env_start += rf"{{{width}\textwidth}}"

        util.record()
        util.record(el.identifier)
        util.record(el.classes)
        util.record("height", height_raw)
        util.record("width", width)
        util.record("align", align)
        util.record(env_start)

        # NOTE: First only needs a start, final only needs a stop. Because of
        #       stupid newline rules, each on interior needs to stop the last
        #       minipage and start its own.
        if "minipage-first" in el.classes:
            out = pf.Div(pf.RawBlock(env_start, format="latex"), el)
        elif "minipage-final" in el.classes:
            out = pf.Div(
                pf.RawBlock(env_stop + env_start, format="latex"),
                el,
                pf.RawBlock(env_stop, format="latex"),
            )
        else:
            out = pf.Div(pf.RawBlock(env_stop + env_start, format="latex"), el)

        util.record(json.dumps(out.to_json(), indent=2))
        return out

    def __call__(self, el: pf.Element):

        if isinstance(el, pf.Div) and "minipage" in el.classes:
            el = self.hydrate_minipage(el)

        return el


filter = util.create_run_filter(FilterMinipage)
